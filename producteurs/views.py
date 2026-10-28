from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, TemplateView

from core.models import Campagne, Section
from core.vues import AccesMixin, Creation, Liste, Modification, Suppression, reponse_csv
from paiements.models import situation_producteur

from .forms import AugmentationQuotaForm, CertificationForm, ParcelleForm, ProducteurForm
from .models import AugmentationQuota, CertificationProducteur, Parcelle, Producteur, Programme


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
            certifications=p.certifications.select_related("programme", "campagne"),
            augmentations=AugmentationQuota.objects.filter(certification__producteur=p).select_related(
                "certification__programme", "demande_par", "decide_par"),
            achats=p.achats.filter(**filtre).select_related("magasin", "programme")[:50],
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
    filtres = ("statut_eudr", "certifiee", "producteur__section")

    def get_queryset(self):
        return super().get_queryset().select_related("producteur")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            sections=Section.objects.all(),
            statuts=Parcelle.EUDR_CHOICES,
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
def infos_producteur(request, pk):
    """Parcelles et certifications d'un producteur (pour le formulaire d'achat)."""
    producteur = get_object_or_404(Producteur, pk=pk)
    campagne = Campagne.objects.filter(pk=request.GET.get("campagne")).first() or Campagne.objects.active()
    certifications = []
    if campagne:
        for c in producteur.certifications.filter(campagne=campagne).select_related("programme"):
            certifications.append({
                "programme": c.programme_id, "code": c.programme.code, "statut": c.get_statut_display(),
                "certifie": c.statut == "certifie", "quota": float(c.quota_kg),
                "superficie": float(c.superficie), "explication": c.explication_quota,
                "augmentations": float(c.augmentations_approuvees_kg), "livre": float(c.volume_achete()),
                "restant": float(c.volume_restant()), "prime_kg": float(c.programme.prime_kg),
                "url_augmentation": reverse("producteurs:augmentation_creer") + f"?certification={c.pk}",
            })
    return JsonResponse({
        "code": producteur.code,
        "nom": producteur.nom_complet,
        "carte": producteur.numero_carte_ccc,
        "section": str(producteur.section or ""),
        "village": producteur.village,
        "superficie": float(producteur.superficie_totale),
        "parcelles": [{"id": p.id, "libelle": str(p)} for p in producteur.parcelles.all()],
        "certifications": certifications,
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
         "oui" if pa.certifiee else "non", pa.get_statut_eudr_display()]
        for pa in Parcelle.objects.select_related("producteur__section")
    )
    return reponse_csv(
        "parcelles_tracabilite.csv",
        ["Code parcelle", "Code producteur", "Producteur", "Section", "Localité", "Superficie (ha)", "Latitude",
         "Longitude", "Polygone GeoJSON", "Année création", "Dans le périmètre certifié", "Statut EUDR"],
        lignes,
    )


class CertificationCreation(Creation):
    model = CertificationProducteur
    form_class = CertificationForm
    message = "Certification enregistrée."

    def get_initial(self):
        return {"producteur": self.request.GET.get("producteur")}

    def get_success_url(self):
        return self.object.producteur.get_absolute_url()


class CertificationModification(Modification):
    model = CertificationProducteur
    form_class = CertificationForm
    message = "Certification modifiée."

    def get_success_url(self):
        return self.object.producteur.get_absolute_url()


class CertificationSuppression(Suppression):
    model = CertificationProducteur

    def get_success_url(self):
        return reverse("producteurs:detail", args=[self.object.producteur_id])


def suivi_certifications(request):
    """Certifications filtrées, avec volume estimé, acheté et restant (contrôle du sur-achat certifié)."""
    g = request.GET
    campagne = Campagne.objects.filter(pk=g.get("campagne")).first() if g.get("campagne") else Campagne.objects.active()
    qs = CertificationProducteur.objects.select_related("producteur__section", "programme", "campagne")
    if campagne:
        qs = qs.filter(campagne=campagne)
    for champ in ("programme", "statut"):
        if g.get(champ):
            qs = qs.filter(**{champ: g[champ]})
    if g.get("q"):
        qs = qs.filter(Q(producteur__nom__icontains=g["q"]) | Q(producteur__prenoms__icontains=g["q"])
                       | Q(producteur__code__icontains=g["q"]))
    lignes = []
    for c in qs.order_by("programme__code", "producteur__nom"):
        quota, achete = c.quota_kg, c.volume_achete()
        lignes.append({"c": c, "superficie": c.superficie, "quota": quota, "achete": achete,
                       "restant": max(quota - achete, 0), "taux": (achete / quota * 100) if quota else None})
    return campagne, lignes


class CertificationListe(AccesMixin, TemplateView):
    model = CertificationProducteur
    template_name = "producteurs/certification_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        campagne, lignes = suivi_certifications(self.request)
        par_programme = {}
        for l in lignes:
            if l["c"].statut != "certifie":
                continue
            t = par_programme.setdefault(l["c"].programme, {"producteurs": 0, "superficie": 0, "quota": 0, "achete": 0})
            t["producteurs"] += 1
            t["superficie"] += l["superficie"]
            t["quota"] += l["quota"]
            t["achete"] += l["achete"]
        ctx.update(
            campagne=campagne, campagnes=Campagne.objects.all(), lignes=lignes,
            programmes=Programme.objects.all(), statuts=CertificationProducteur.STATUT_CHOICES,
            par_programme=par_programme,
        )
        return ctx


@login_required
@permission_required("producteurs.view_certificationproducteur", raise_exception=True)
def export_certifications(request):
    """Liste des membres (format tableur) pour les inspections internes et les audits RA / ARS 1000."""
    _, lignes = suivi_certifications(request)
    return reponse_csv(
        "membres_certifies.csv",
        ["Programme", "Campagne", "Code producteur", "N° membre", "Producteur", "Sexe", "Section", "Village",
         "Statut", "Niveau", "Superficie certifiée (ha)", "Production estimée (kg)", "Acheté certifié (kg)",
         "Restant (kg)", "Inspection interne", "Audit"],
        ([l["c"].programme.code, l["c"].campagne, l["c"].producteur.code, l["c"].numero_membre,
          l["c"].producteur.nom_complet, l["c"].producteur.get_sexe_display(), l["c"].producteur.section or "",
          l["c"].producteur.village, l["c"].get_statut_display(), l["c"].get_niveau_display(), l["superficie"],
          l["quota"], l["achete"], l["restant"], l["c"].date_inspection_interne or "", l["c"].date_audit or ""]
         for l in lignes),
    )


class AugmentationListe(Liste):
    model = AugmentationQuota
    filtres = ("statut",)
    champs_recherche = ("certification__producteur__nom", "certification__producteur__prenoms",
                        "certification__producteur__code", "certification__producteur__numero_carte_ccc")

    def get_queryset(self):
        return super().get_queryset().select_related(
            "certification__producteur", "certification__programme", "certification__campagne",
            "demande_par", "decide_par")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuts"] = AugmentationQuota.STATUT_CHOICES
        ctx["peut_decider"] = self.request.user.has_perm("producteurs.approuver_augmentationquota")
        return ctx


class AugmentationCreation(Creation):
    model = AugmentationQuota
    form_class = AugmentationQuotaForm
    template_name = "producteurs/augmentationquota_form.html"
    message = "Demande enregistrée. Le quota augmentera après approbation par un responsable."
    success_url = reverse_lazy("producteurs:augmentations")

    def get_initial(self):
        return {"certification": self.request.GET.get("certification")}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titre"] = "Demande d'augmentation de quota de certification"
        pk = self.request.GET.get("certification")
        ctx["certification"] = CertificationProducteur.objects.filter(pk=pk).first() if pk else None
        return ctx

    def form_valid(self, form):
        form.instance.demande_par = self.request.user
        return super().form_valid(form)


@require_POST
@login_required
@permission_required("producteurs.approuver_augmentationquota", raise_exception=True)
def augmentation_decision(request, pk):
    demande = get_object_or_404(AugmentationQuota, pk=pk)
    approuver = request.POST.get("decision") == "approuver"
    try:
        demande.decider(request.user, approuver, request.POST.get("commentaire", "").strip())
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    else:
        c = demande.certification
        if approuver:
            messages.success(request, f"Augmentation approuvée : nouveau quota de {c.producteur.nom_complet} = "
                                      f"{c.quota_kg:,.0f} kg.".replace(",", " "))
        else:
            messages.success(request, "Demande rejetée.")
    return redirect("producteurs:augmentations")


@login_required
@permission_required("producteurs.view_augmentationquota", raise_exception=True)
def augmentation_piece(request, pk):
    """Pièce justificative, accessible seulement aux utilisateurs connectés et autorisés."""
    demande = get_object_or_404(AugmentationQuota, pk=pk)
    if not demande.piece_jointe:
        raise Http404
    return FileResponse(demande.piece_jointe.open("rb"), filename=demande.piece_jointe.name.rsplit("/", 1)[-1])
