from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import DetailView

from core.models import Campagne, Magasin, PrixDuJour
from core.vues import AccesMixin, Creation, Liste, Modification, Suppression, reponse_csv
from producteurs.models import Programme

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
    if g.get("certification") == "certifie":
        qs = qs.filter(poids_certifie__gt=0)
    elif g.get("certification") == "non_certifie":
        qs = qs.filter(poids_certifie=0)
    elif g.get("certification"):
        qs = qs.filter(programme_id=g["certification"])
    return qs


class AchatListe(Liste):
    model = Achat
    champs_recherche = ("numero", "producteur__nom", "producteur__prenoms", "producteur__code")

    def get_queryset(self):
        qs = super().get_queryset().select_related("producteur", "magasin", "campagne", "programme")
        return filtrer_achats(self.request, qs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["totaux"] = self.get_queryset().aggregate(
            poids=Sum("poids_net"), montant=Sum("montant"), sacs=Sum("nombre_sacs"), nombre=Count("id"),
            certifie=Sum("poids_certifie"), non_certifie=Sum("poids_non_certifie"), primes=Sum("montant_prime"),
        )
        ctx["programmes"] = Programme.objects.all()
        ctx["campagnes"] = Campagne.objects.all()
        ctx["magasins"] = Magasin.objects.all()
        return ctx


class AchatDetail(AccesMixin, DetailView):
    model = Achat

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lignes_lot"] = self.object.lignes_lot.select_related("lot")
        return ctx


class AchatFormMixin:
    model = Achat
    form_class = AchatForm
    template_name = "achats/achat_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["prix_campagnes"] = {str(c.pk): float(c.prix_kg) for c in Campagne.objects.all()}
        ctx["prix_du_jour"] = [
            {"campagne": p.campagne_id, "date": p.date.isoformat(), "magasin": p.magasin_id, "prix": float(p.prix_kg)}
            for p in PrixDuJour.objects.filter(campagne__active=True)
        ]
        objet = getattr(self, "object", None)
        ctx["restant_initial"] = float(objet.poids_certifie) if objet and objet.pk else 0
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

    def form_valid(self, form):
        if self.object.lignes_lot.exists():
            messages.error(self.request, "Cet achat est placé dans un lot : retirez-le du lot avant de le supprimer.")
            return redirect(self.object)
        return super().form_valid(form)


@login_required
@permission_required("achats.view_achat", raise_exception=True)
def recu(request, pk):
    achat = get_object_or_404(
        Achat.objects.select_related("producteur__section", "magasin", "campagne", "parcelle", "programme"), pk=pk
    )
    certifications = achat.producteur.certifications.filter(campagne=achat.campagne).select_related("programme")
    certification = (certifications.filter(programme=achat.programme).first() if achat.programme_id
                     else certifications.filter(statut="certifie").first())
    quota = None
    if certification is not None:
        # Situation du quota au moment de ce reçu (achats antérieurs et celui-ci).
        anterieurs = Achat.objects.filter(
            producteur=achat.producteur, campagne=achat.campagne, programme=certification.programme,
        ).filter(Q(date__lt=achat.date) | Q(date=achat.date, pk__lte=achat.pk))
        livre = anterieurs.aggregate(p=Sum("poids_certifie"))["p"] or 0
        quota = {"total": certification.quota_kg, "livre": livre,
                 "reste": max(certification.quota_kg - livre, 0)}
    return render(request, "achats/recu.html", {"achat": achat, "certification": certification, "quota": quota})


@login_required
@permission_required("achats.view_achat", raise_exception=True)
def export_achats(request):
    qs = filtrer_achats(request, Achat.objects.select_related(
        "producteur", "magasin", "parcelle", "campagne", "programme").prefetch_related("lignes_lot__lot"))
    lignes = (
        [a.numero, a.date, a.campagne, a.magasin.code, a.producteur.code, a.producteur.nom_complet,
         a.parcelle.code if a.parcelle else "", a.nombre_sacs, a.poids_brut, a.tare, a.humidite or "",
         a.refaction, a.poids_net, a.programme.code if a.programme else "", a.poids_certifie,
         a.poids_non_certifie, a.get_qualite_display(), a.prix_kg, a.get_source_prix_display(), a.montant,
         a.montant_prime, ", ".join(l.lot.numero for l in a.lignes_lot.all())]
        for a in qs
    )
    return reponse_csv(
        "achats.csv",
        ["N° reçu", "Date", "Campagne", "Magasin", "Code producteur", "Producteur", "Parcelle", "Sacs",
         "Poids brut", "Tare", "Humidité %", "Réfaction %", "Poids net", "Programme", "Poids certifié",
         "Poids non certifié", "Qualité", "Prix/kg", "Origine du prix", "Montant", "Prime certification", "Lots"],
        lignes,
    )
