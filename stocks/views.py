from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView

from achats.models import Achat
from core.models import Campagne, Magasin
from core.vues import AccesMixin, Creation, Liste, Modification, Suppression, reponse_csv

from .forms import LivraisonForm, LotForm
from .models import Livraison, Lot, stock_par_magasin


class Stock(AccesMixin, TemplateView):
    model = Lot
    template_name = "stocks/stock.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        campagne_id = self.request.GET.get("campagne")
        campagne = Campagne.objects.filter(pk=campagne_id).first() if campagne_id else None
        lignes = stock_par_magasin(campagne)
        ctx.update(
            lignes=lignes,
            campagne=campagne,
            campagnes=Campagne.objects.all(),
            total_poids=sum(l["poids"] for l in lignes),
            total_sacs=sum(l["sacs"] for l in lignes),
            total_valeur=sum(l["valeur"] for l in lignes),
            lots_prets=Lot.objects.filter(statut="ferme").select_related("magasin"),
        )
        return ctx


class LotListe(Liste):
    model = Lot
    champs_recherche = ("numero", "magasin__nom")
    filtres = ("statut", "magasin", "campagne")

    def get_queryset(self):
        return super().get_queryset().select_related("magasin", "campagne").annotate(
            poids=Sum("achats__poids_net"), sacs=Sum("achats__nombre_sacs")
        ).order_by("-date_creation", "-id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(magasins=Magasin.objects.all(), campagnes=Campagne.objects.all(), statuts=Lot.STATUT_CHOICES)
        return ctx


class LotDetail(AccesMixin, DetailView):
    model = Lot

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lot = self.object
        ctx["achats"] = lot.achats.select_related("producteur", "parcelle")
        ctx["producteurs"] = (
            lot.achats.values("producteur__code", "producteur__nom", "producteur__prenoms")
            .annotate(poids=Sum("poids_net")).order_by("-poids")
        )
        if lot.statut == "ouvert":
            ctx["disponibles"] = Achat.objects.filter(
                lot__isnull=True, magasin=lot.magasin, campagne=lot.campagne
            ).select_related("producteur")
        return ctx


class LotCreation(Creation):
    model = Lot
    form_class = LotForm
    message = "Lot créé. Ajoutez-y maintenant les achats."


class LotModification(Modification):
    model = Lot
    form_class = LotForm


class LotSuppression(Suppression):
    model = Lot
    success_url = reverse_lazy("stocks:lots")

    def form_valid(self, form):
        if self.object.statut == "livre":
            messages.error(self.request, "Un lot livré ne peut pas être supprimé.")
            return redirect(self.object.get_absolute_url())
        return super().form_valid(form)


@require_POST
@login_required
@permission_required("stocks.change_lot", raise_exception=True)
def lot_achats(request, pk):
    """Ajoute ou retire des achats d'un lot ouvert."""
    lot = get_object_or_404(Lot, pk=pk)
    if lot.statut != "ouvert":
        messages.error(request, "Le lot n'est pas ouvert : rouvrez-le pour modifier son contenu.")
        return redirect(lot)
    ids = request.POST.getlist("achats")
    if request.POST.get("action") == "retirer":
        n = lot.achats.filter(pk__in=ids).update(lot=None)
        messages.success(request, f"{n} achat(s) retiré(s) du lot.")
    else:
        n = Achat.objects.filter(
            pk__in=ids, lot__isnull=True, magasin=lot.magasin, campagne=lot.campagne
        ).update(lot=lot)
        messages.success(request, f"{n} achat(s) ajouté(s) au lot.")
    return redirect(lot)


@require_POST
@login_required
@permission_required("stocks.change_lot", raise_exception=True)
def lot_statut(request, pk):
    lot = get_object_or_404(Lot, pk=pk)
    nouveau = request.POST.get("statut")
    if lot.statut == "livre":
        messages.error(request, "Ce lot est déjà livré.")
    elif nouveau == "ferme":
        if not lot.achats.exists():
            messages.error(request, "Impossible de fermer un lot vide.")
        else:
            lot.statut = "ferme"
            lot.save(update_fields=["statut"])
            messages.success(request, "Lot fermé : il est prêt à être livré.")
    elif nouveau == "ouvert":
        lot.statut = "ouvert"
        lot.save(update_fields=["statut"])
        messages.success(request, "Lot rouvert.")
    return redirect(lot)


@login_required
@permission_required("stocks.view_lot", raise_exception=True)
def lot_tracabilite(request, pk):
    """Liste des producteurs et parcelles d'origine d'un lot (déclaration de traçabilité)."""
    lot = get_object_or_404(Lot, pk=pk)
    lignes = (
        [lot.numero, a.numero, a.date, a.producteur.code, a.producteur.nom_complet,
         a.parcelle.code if a.parcelle else "", a.parcelle.latitude if a.parcelle else "",
         a.parcelle.longitude if a.parcelle else "", a.parcelle.superficie_ha if a.parcelle else "",
         a.parcelle.get_statut_eudr_display() if a.parcelle else "", a.poids_net]
        for a in lot.achats.select_related("producteur", "parcelle")
    )
    return reponse_csv(
        f"tracabilite_{lot.numero}.csv",
        ["Lot", "N° reçu", "Date", "Code producteur", "Producteur", "Parcelle", "Latitude", "Longitude",
         "Superficie (ha)", "Statut EUDR", "Poids net (kg)"],
        lignes,
    )


class LivraisonListe(Liste):
    model = Livraison
    champs_recherche = ("numero", "exportateur__nom", "numero_bordereau", "immatriculation")
    filtres = ("exportateur",)

    def get_queryset(self):
        return super().get_queryset().select_related("exportateur").prefetch_related("lots")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_poids"] = self.get_queryset().aggregate(p=Sum("poids_livre"))["p"] or 0
        return ctx


class LivraisonDetail(AccesMixin, DetailView):
    model = Livraison


class LivraisonFormMixin:
    model = Livraison
    form_class = LivraisonForm

    @transaction.atomic
    def form_valid(self, form):
        anciens = set(self.object.lots.values_list("pk", flat=True)) if self.object else set()
        reponse = super().form_valid(form)
        nouveaux = set(self.object.lots.values_list("pk", flat=True))
        Lot.objects.filter(pk__in=anciens - nouveaux).update(statut="ferme")
        Lot.objects.filter(pk__in=nouveaux).update(statut="livre")
        return reponse


class LivraisonCreation(LivraisonFormMixin, Creation):
    message = "Livraison enregistrée. Les lots sont marqués comme livrés."


class LivraisonModification(LivraisonFormMixin, Modification):
    message = "Livraison modifiée."


class LivraisonSuppression(Suppression):
    model = Livraison
    success_url = reverse_lazy("stocks:livraisons")

    @transaction.atomic
    def form_valid(self, form):
        self.object.lots.update(statut="ferme")
        return super().form_valid(form)
