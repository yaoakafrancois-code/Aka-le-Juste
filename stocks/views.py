from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView

from achats.models import Achat
from core.models import Campagne, Cooperative, Magasin
from core.vues import AccesMixin, Creation, Liste, Modification, Suppression, reponse_csv
from producteurs.models import Programme

from .forms import AnalyseQualiteForm, LivraisonForm, LotForm
from .models import LigneLot, Livraison, Lot, stock_par_magasin


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
            totaux={cle: sum(l[cle] for l in lignes) for cle in ("poids", "certifie", "non_certifie", "sacs",
                                                                  "hors_lot")},
            lots_prets=Lot.objects.filter(statut="ferme").select_related("magasin", "programme"),
        )
        return ctx


class LotListe(Liste):
    model = Lot
    champs_recherche = ("numero", "magasin__nom")
    filtres = ("statut", "magasin", "campagne", "programme")

    def get_queryset(self):
        qs = super().get_queryset().select_related("magasin", "campagne", "programme").annotate(
            poids=Sum("lignes__poids"), sacs=Sum("lignes__sacs")
        ).order_by("-date_creation", "-id")
        if self.request.GET.get("type") == "conventionnel":
            qs = qs.filter(programme__isnull=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(magasins=Magasin.objects.all(), campagnes=Campagne.objects.all(), statuts=Lot.STATUT_CHOICES,
                   programmes=Programme.objects.all())
        return ctx


def achats_disponibles(lot):
    """Achats du magasin et de la campagne du lot dont une part du bon type n'est pas encore placée."""
    achats = Achat.objects.filter(magasin=lot.magasin, campagne=lot.campagne).select_related("producteur")
    if lot.certifie:
        achats = achats.filter(programme=lot.programme, poids_certifie__gt=0)
        champ = "poids_certifie"
    else:
        achats = achats.filter(poids_non_certifie__gt=0)
        champ = "poids_non_certifie"
    achats = achats.annotate(
        place=Sum("lignes_lot__poids", filter=Q(lignes_lot__certifie=lot.certifie), default=0)
    ).annotate(disponible=F(champ) - F("place")).filter(disponible__gt=0)
    return achats.order_by("date", "id")


class LotDetail(AccesMixin, DetailView):
    model = Lot

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lot = self.object
        ctx["lignes"] = lot.lignes.select_related("achat__producteur", "achat__parcelle")
        ctx["producteurs"] = (
            lot.lignes.values("achat__producteur__code", "achat__producteur__nom", "achat__producteur__prenoms")
            .annotate(poids=Sum("poids")).order_by("-poids")
        )
        ctx["form_qualite"] = AnalyseQualiteForm(instance=lot)
        if lot.statut == "ouvert":
            ctx["disponibles"] = achats_disponibles(lot)
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
@transaction.atomic
def lot_achats(request, pk):
    """Ajoute des achats à un lot ouvert ou en retire des lignes."""
    lot = get_object_or_404(Lot, pk=pk)
    if lot.statut != "ouvert":
        messages.error(request, "Le lot n'est pas ouvert : rouvrez-le pour modifier son contenu.")
        return redirect(lot)
    if request.POST.get("action") == "retirer":
        n, _ = lot.lignes.filter(pk__in=request.POST.getlist("lignes")).delete()
        messages.success(request, f"{n} ligne(s) retirée(s) du lot.")
    else:
        n = 0
        for achat in Achat.objects.filter(pk__in=request.POST.getlist("achats")):
            if LigneLot.placer(lot, achat):
                n += 1
        messages.success(request, f"{n} achat(s) ajouté(s) au lot.")
    return redirect(lot)


@require_POST
@login_required
@permission_required("stocks.change_lot", raise_exception=True)
def lot_qualite(request, pk):
    lot = get_object_or_404(Lot, pk=pk)
    form = AnalyseQualiteForm(request.POST, instance=lot)
    if form.is_valid():
        form.save()
        messages.success(request, f"Analyse qualité enregistrée : {lot.get_grade_display() or 'grade non déterminé'}.")
    else:
        messages.error(request, "Analyse non enregistrée : vérifiez les valeurs saisies.")
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
        if not lot.lignes.exists():
            messages.error(request, "Impossible de fermer un lot vide.")
        else:
            lot.statut = "ferme"
            lot.save(update_fields=["statut"])
            messages.success(request, "Lot fermé : il est prêt à être livré.")
            if not lot.grade:
                messages.warning(request, "Pensez à saisir l'analyse qualité avant l'expédition.")
    elif nouveau == "ouvert":
        lot.statut = "ouvert"
        lot.save(update_fields=["statut"])
        messages.success(request, "Lot rouvert.")
    return redirect(lot)


ENTETES_TRACABILITE = [
    "Lot", "Type de produit", "N° reçu", "Date d'achat", "Code producteur", "Carte producteur", "Producteur",
    "Section", "Village", "Parcelle", "Latitude", "Longitude", "Superficie (ha)", "Statut EUDR", "Poids (kg)",
]


def lignes_tracabilite(lots):
    for lot in lots:
        for l in lot.lignes.select_related("achat__producteur__section", "achat__parcelle"):
            a, pa = l.achat, l.achat.parcelle
            yield [lot.numero, lot.type_produit, a.numero, a.date, a.producteur.code, a.producteur.numero_carte_ccc,
                   a.producteur.nom_complet, a.producteur.section or "", a.producteur.village,
                   pa.code if pa else "", pa.latitude if pa else "", pa.longitude if pa else "",
                   pa.superficie_ha if pa else "", pa.get_statut_eudr_display() if pa else "", l.poids]


@login_required
@permission_required("stocks.view_lot", raise_exception=True)
def lot_tracabilite(request, pk):
    """Producteurs et parcelles d'origine d'un lot (déclaration de traçabilité)."""
    lot = get_object_or_404(Lot, pk=pk)
    return reponse_csv(f"tracabilite_{lot.numero}.csv", ENTETES_TRACABILITE, lignes_tracabilite([lot]))


class LivraisonListe(Liste):
    model = Livraison
    champs_recherche = ("numero", "numero_connaissement", "exportateur__nom", "immatriculation", "chauffeur")
    filtres = ("exportateur",)

    def get_queryset(self):
        return super().get_queryset().select_related("exportateur").prefetch_related("lots__programme")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_poids"] = self.get_queryset().aggregate(p=Sum("poids_livre"))["p"] or 0
        return ctx


class LivraisonDetail(AccesMixin, DetailView):
    model = Livraison


class LivraisonFormMixin:
    model = Livraison
    form_class = LivraisonForm

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault("lots", self.request.GET.getlist("lot"))
        return initial

    @transaction.atomic
    def form_valid(self, form):
        anciens = set(self.object.lots.values_list("pk", flat=True)) if self.object else set()
        reponse = super().form_valid(form)
        nouveaux = set(self.object.lots.values_list("pk", flat=True))
        Lot.objects.filter(pk__in=anciens - nouveaux).update(statut="ferme")
        Lot.objects.filter(pk__in=nouveaux).update(statut="livre")
        if self.object.nombre_sacs is None:
            self.object.nombre_sacs = self.object.sacs_lots
            self.object.save(update_fields=["nombre_sacs"])
        return reponse


class LivraisonCreation(LivraisonFormMixin, Creation):
    message = "Livraison enregistrée. Les lots sont marqués comme livrés ; imprimez le connaissement."


class LivraisonModification(LivraisonFormMixin, Modification):
    message = "Livraison modifiée."


class LivraisonSuppression(Suppression):
    model = Livraison
    success_url = reverse_lazy("stocks:livraisons")

    @transaction.atomic
    def form_valid(self, form):
        self.object.lots.update(statut="ferme")
        return super().form_valid(form)


@login_required
@permission_required("stocks.view_livraison", raise_exception=True)
def connaissement(request, pk):
    """Fiche de suivi / connaissement imprimable, avec l'annexe de traçabilité des producteurs."""
    livraison = get_object_or_404(Livraison.objects.select_related("exportateur"), pk=pk)
    lots = livraison.lots.select_related("magasin", "programme", "campagne")
    annexe = (
        LigneLot.objects.filter(lot__in=lots)
        .values("achat__producteur__code", "achat__producteur__numero_carte_ccc", "achat__producteur__nom",
                "achat__producteur__prenoms", "achat__producteur__village", "achat__parcelle__code",
                "achat__parcelle__latitude", "achat__parcelle__longitude")
        .annotate(poids=Sum("poids"), sacs=Sum("sacs"))
        .order_by("achat__producteur__nom", "achat__producteur__prenoms")
    )
    premier = lots.first()
    return render(request, "stocks/connaissement.html", {
        "livraison": livraison,
        "lots": lots,
        "annexe": annexe,
        "campagne": premier.campagne if premier else None,
        "programme": premier.programme if premier else None,
        "magasins": sorted({lot.magasin.nom for lot in lots}),
        "nombre_producteurs": len(annexe),
        "exemplaires": ["Coopérative", "Transporteur", "Exportateur", "Conseil du Café-Cacao"]
        if request.GET.get("exemplaires") else [""],
    })


@login_required
@permission_required("stocks.view_livraison", raise_exception=True)
def export_connaissements(request):
    """Données des expéditions au format tableur, pour la saisie dans le système du Conseil du Café-Cacao."""
    coop = Cooperative.courante()
    lignes = []
    for l in Livraison.objects.select_related("exportateur").prefetch_related("lots__magasin", "lots__campagne"):
        lot = l.premier_lot
        lignes.append([
            l.numero, l.numero_connaissement, l.date, lot.campagne if lot else "", coop.code_ccc, coop.nom,
            coop.region, coop.departement, coop.sous_prefecture,
            ", ".join(sorted({x.magasin.nom for x in l.lots.all()})), l.exportateur.nom, l.exportateur.code_ccc,
            l.get_destination_display(), l.adresse_destination, l.type_produit, l.grade,
            ", ".join(x.numero for x in l.lots.all()), l.nombre_sacs or "", l.poids_brut or "", l.poids_livre,
            l.poids_reconnu or "", l.transporteur, l.immatriculation, l.immatriculation_remorque, l.chauffeur,
            l.permis_chauffeur,
        ])
    return reponse_csv(
        "connaissements.csv",
        ["N° livraison", "N° connaissement", "Date", "Campagne", "Code coopérative CCC", "Coopérative", "Région",
         "Département", "Sous-préfecture", "Magasin(s)", "Exportateur", "Code exportateur CCC", "Destination",
         "Adresse destination", "Type de produit", "Grade", "Lots", "Sacs", "Poids brut (kg)", "Poids net (kg)",
         "Poids reconnu (kg)", "Transporteur", "Camion", "Remorque", "Chauffeur", "Permis"],
        lignes,
    )


@login_required
@permission_required("stocks.view_livraison", raise_exception=True)
def livraison_tracabilite(request, pk):
    livraison = get_object_or_404(Livraison, pk=pk)
    return reponse_csv(f"tracabilite_{livraison.numero}.csv", ENTETES_TRACABILITE,
                       lignes_tracabilite(livraison.lots.all()))
