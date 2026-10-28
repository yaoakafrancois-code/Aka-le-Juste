from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import DetailView

from core.models import Campagne, Magasin
from core.vues import AccesMixin, Creation, Liste, Modification, Suppression, reponse_csv

from .forms import AchatForm
from .models import Achat


def filtrer_achats(request, qs):
    g = request.GET
    if g.get("campagne"):
        qs = qs.filter(campagne_id=g["campagne"])
    if g.get("magasin"):
        qs = qs.filter(magasin_id=g["magasin"])
    if g.get("producteur"):
        qs = qs.filter(producteur_id=g["producteur"])
    if g.get("du"):
        qs = qs.filter(date__gte=g["du"])
    if g.get("au"):
        qs = qs.filter(date__lte=g["au"])
    return qs


class AchatListe(Liste):
    model = Achat
    champs_recherche = ("numero", "producteur__nom", "producteur__prenoms", "producteur__code")

    def get_queryset(self):
        qs = super().get_queryset().select_related("producteur", "magasin", "lot", "campagne")
        return filtrer_achats(self.request, qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["totaux"] = self.get_queryset().aggregate(
            poids=Sum("poids_net"), montant=Sum("montant"), sacs=Sum("nombre_sacs"), nombre=Count("id")
        )
        ctx["campagnes"] = Campagne.objects.all()
        ctx["magasins"] = Magasin.objects.all()
        return ctx


class AchatDetail(AccesMixin, DetailView):
    model = Achat


class AchatFormMixin:
    model = Achat
    form_class = AchatForm
    template_name = "achats/achat_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["prix_campagnes"] = {str(c.pk): float(c.prix_kg) for c in Campagne.objects.all()}
        return ctx


class AchatCreation(AchatFormMixin, Creation):
    message = "Achat enregistré."

    def get_initial(self):
        initial = {}
        for cle in ("producteur", "magasin"):
            if self.request.GET.get(cle):
                initial[cle] = self.request.GET[cle]
        dernier = Achat.objects.filter(agent=self.request.user).first()
        if dernier and "magasin" not in initial:
            initial["magasin"] = dernier.magasin_id
        return initial

    def get_success_url(self):
        return reverse_lazy("achats:detail", args=[self.object.pk])


class AchatModification(AchatFormMixin, Modification):
    message = "Achat modifié."


class AchatSuppression(Suppression):
    model = Achat
    success_url = reverse_lazy("achats:liste")


@login_required
@permission_required("achats.view_achat", raise_exception=True)
def recu(request, pk):
    achat = get_object_or_404(Achat.objects.select_related("producteur", "magasin", "campagne", "parcelle"), pk=pk)
    return render(request, "achats/recu.html", {"achat": achat})


@login_required
@permission_required("achats.view_achat", raise_exception=True)
def export_achats(request):
    qs = filtrer_achats(request, Achat.objects.select_related("producteur", "magasin", "parcelle", "lot", "campagne"))
    lignes = (
        [a.numero, a.date, a.campagne, a.magasin.code, a.producteur.code, a.producteur.nom_complet,
         a.parcelle.code if a.parcelle else "", a.nombre_sacs, a.poids_brut, a.tare, a.humidite or "",
         a.refaction, a.poids_net, a.get_qualite_display(), a.prix_kg, a.montant, a.lot or ""]
        for a in qs
    )
    return reponse_csv(
        "achats.csv",
        ["N° reçu", "Date", "Campagne", "Magasin", "Code producteur", "Producteur", "Parcelle", "Sacs",
         "Poids brut", "Tare", "Humidité %", "Réfaction %", "Poids net", "Qualité", "Prix/kg", "Montant", "Lot"],
        lignes,
    )
