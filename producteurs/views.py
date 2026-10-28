from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView

from core.models import Campagne, Section
from core.vues import AccesMixin, Creation, Liste, Modification, Suppression, reponse_csv
from paiements.models import situation_producteur

from .forms import ParcelleForm, ProducteurForm
from .models import Parcelle, Producteur


class ProducteurListe(Liste):
    model = Producteur
    champs_recherche = ("code", "nom", "prenoms", "telephone", "village", "numero_carte_ccc")
    filtres = ("section", "actif")

    def get_queryset(self):
        return super().get_queryset().select_related("section")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sections"] = Section.objects.all()
        return ctx


class ProducteurDetail(AccesMixin, DetailView):
    model = Producteur

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        campagne_id = self.request.GET.get("campagne")
        campagne = Campagne.objects.filter(pk=campagne_id).first() if campagne_id else Campagne.objects.active()
        p = self.object
        filtre = {"campagne": campagne} if campagne else {}
        ctx.update(
            campagne=campagne,
            campagnes=Campagne.objects.all(),
            situation=situation_producteur(p, campagne),
            situation_globale=situation_producteur(p),
            parcelles=p.parcelles.all(),
            achats=p.achats.filter(**filtre).select_related("magasin", "lot")[:50],
            paiements=p.paiements.filter(**filtre)[:50],
            avances=p.avances.filter(**filtre)[:50],
            primes=p.primes.filter(**filtre)[:50],
        )
        return ctx


class ProducteurCreation(Creation):
    model = Producteur
    form_class = ProducteurForm
    message = "Producteur enregistré."


class ProducteurModification(Modification):
    model = Producteur
    form_class = ProducteurForm
    message = "Producteur modifié."


class ProducteurSuppression(Suppression):
    model = Producteur
    success_url = reverse_lazy("producteurs:liste")


class ParcelleListe(Liste):
    model = Parcelle
    template_name = "producteurs/parcelle_list.html"
    champs_recherche = ("code", "producteur__nom", "producteur__prenoms", "producteur__code", "localite")
    filtres = ("statut_eudr", "certification", "producteur__section")

    def get_queryset(self):
        return super().get_queryset().select_related("producteur")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            sections=Section.objects.all(),
            statuts=Parcelle.EUDR_CHOICES,
            certifications=Parcelle.CERTIFICATION_CHOICES,
        )
        return ctx


class ParcelleCreation(Creation):
    model = Parcelle
    form_class = ParcelleForm
    message = "Parcelle enregistrée."

    def get_initial(self):
        return {"producteur": self.request.GET.get("producteur")}

    def get_success_url(self):
        return self.object.producteur.get_absolute_url()


class ParcelleModification(Modification):
    model = Parcelle
    form_class = ParcelleForm
    message = "Parcelle modifiée."

    def get_success_url(self):
        return self.object.producteur.get_absolute_url()


class ParcelleSuppression(Suppression):
    model = Parcelle

    def get_success_url(self):
        return reverse("producteurs:detail", args=[self.object.producteur_id])


@login_required
@permission_required("producteurs.view_parcelle", raise_exception=True)
def parcelles_json(request, pk):
    """Parcelles d'un producteur (pour le formulaire d'achat)."""
    producteur = get_object_or_404(Producteur, pk=pk)
    return JsonResponse({
        "parcelles": [{"id": p.id, "libelle": str(p)} for p in producteur.parcelles.all()],
    })


@login_required
@permission_required("producteurs.view_producteur", raise_exception=True)
def export_producteurs(request):
    lignes = (
        [p.code, p.nom, p.prenoms, p.get_sexe_display(), p.date_naissance or "", p.telephone, p.numero_piece,
         p.numero_carte_ccc, p.section or "", p.village, p.date_adhesion or "", "oui" if p.actif else "non"]
        for p in Producteur.objects.select_related("section")
    )
    return reponse_csv(
        "producteurs.csv",
        ["Code", "Nom", "Prénoms", "Sexe", "Naissance", "Téléphone", "Pièce", "Carte producteur", "Section",
         "Village", "Adhésion", "Actif"],
        lignes,
    )


@login_required
@permission_required("producteurs.view_parcelle", raise_exception=True)
def export_parcelles(request):
    """Export de traçabilité (géolocalisation des parcelles) utile pour la conformité EUDR."""
    lignes = (
        [pa.code, pa.producteur.code, pa.producteur.nom_complet, pa.producteur.section or "", pa.localite,
         pa.superficie_ha, pa.latitude or "", pa.longitude or "", pa.polygone_geojson, pa.annee_creation or "",
         pa.get_certification_display(), pa.get_statut_eudr_display()]
        for pa in Parcelle.objects.select_related("producteur__section")
    )
    return reponse_csv(
        "parcelles_tracabilite.csv",
        ["Code parcelle", "Code producteur", "Producteur", "Section", "Localité", "Superficie (ha)", "Latitude",
         "Longitude", "Polygone GeoJSON", "Année création", "Certification", "Statut EUDR"],
        lignes,
    )
