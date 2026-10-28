from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import DecimalField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView

from achats.models import Achat
from core.models import Campagne, Section
from core.vues import AccesMixin, Creation, Liste, Modification, Suppression, reponse_csv
from producteurs.models import Producteur

from .forms import AvanceForm, PaiementForm, PrimeForm
from .models import Avance, Paiement, Prime, situation_producteur


class PrefillProducteur:
    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("producteur"):
            initial["producteur"] = self.request.GET["producteur"]
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pid = self.request.GET.get("producteur")
        if pid:
            producteur = Producteur.objects.filter(pk=pid).first()
            if producteur:
                ctx["situation"] = situation_producteur(producteur)
                ctx["producteur_selectionne"] = producteur
        return ctx


class ListeFinanciere(Liste):
    champs_recherche = ("producteur__nom", "producteur__prenoms", "producteur__code")
    filtres = ("campagne", "producteur")

    def get_queryset(self):
        return super().get_queryset().select_related("producteur", "campagne")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total"] = self.get_queryset().aggregate(t=Sum("montant"))["t"] or 0
        ctx["campagnes"] = Campagne.objects.all()
        ctx["titre_liste"] = self.titre_liste
        ctx["libelle_creation"] = self.libelle_creation
        ctx["url_creation"] = reverse(self.url_creation)
        return ctx


class PaiementListe(ListeFinanciere):
    model = Paiement
    titre_liste, libelle_creation, url_creation = "Paiements", "Nouveau paiement", "paiements:creer"
    champs_recherche = ListeFinanciere.champs_recherche + ("numero", "reference")
    filtres = ListeFinanciere.filtres + ("mode",)


class PaiementCreation(PrefillProducteur, Creation):
    model = Paiement
    form_class = PaiementForm
    template_name = "paiements/form_financier.html"
    message = "Paiement enregistré."

    def get_success_url(self):
        return reverse_lazy("paiements:recu", args=[self.object.pk])


class PaiementModification(Modification):
    model = Paiement
    form_class = PaiementForm
    success_url = reverse_lazy("paiements:liste")


class PaiementSuppression(Suppression):
    model = Paiement
    success_url = reverse_lazy("paiements:liste")


class AvanceListe(ListeFinanciere):
    model = Avance
    titre_liste, libelle_creation, url_creation = "Avances", "Nouvelle avance", "paiements:avance_creer"


class AvanceCreation(PrefillProducteur, Creation):
    model = Avance
    form_class = AvanceForm
    template_name = "paiements/form_financier.html"
    message = "Avance enregistrée."
    success_url = reverse_lazy("paiements:avances")


class AvanceModification(Modification):
    model = Avance
    form_class = AvanceForm
    success_url = reverse_lazy("paiements:avances")


class AvanceSuppression(Suppression):
    model = Avance
    success_url = reverse_lazy("paiements:avances")


class PrimeListe(ListeFinanciere):
    model = Prime
    titre_liste, libelle_creation, url_creation = "Primes", "Nouvelle prime", "paiements:prime_creer"
    filtres = ListeFinanciere.filtres + ("type_prime",)


class PrimeCreation(PrefillProducteur, Creation):
    model = Prime
    form_class = PrimeForm
    template_name = "paiements/form_financier.html"
    message = "Prime enregistrée."
    success_url = reverse_lazy("paiements:primes")


class PrimeModification(Modification):
    model = Prime
    form_class = PrimeForm
    success_url = reverse_lazy("paiements:primes")


class PrimeSuppression(Suppression):
    model = Prime
    success_url = reverse_lazy("paiements:primes")


def soldes_producteurs(campagne=None, section=None, q=""):
    """Producteurs annotés de leurs totaux (achats, primes, paiements, avances) et de leur solde."""
    zero = Value(0, output_field=DecimalField(max_digits=16, decimal_places=2))

    def somme(modele, champ="montant"):
        qs = modele.objects.filter(producteur=OuterRef("pk"))
        if campagne:
            qs = qs.filter(campagne=campagne)
        sous = qs.values("producteur").annotate(t=Sum(champ)).values("t")
        return Coalesce(Subquery(sous, output_field=DecimalField(max_digits=16, decimal_places=2)), zero)

    qs = Producteur.objects.select_related("section").annotate(
        total_poids=somme(Achat, "poids_net"),
        total_achats=somme(Achat),
        total_primes=somme(Prime),
        total_paiements=somme(Paiement),
        total_avances=somme(Avance),
    ).annotate(
        solde=Coalesce("total_achats", zero) + Coalesce("total_primes", zero)
        - Coalesce("total_paiements", zero) - Coalesce("total_avances", zero)
    )
    if section:
        qs = qs.filter(section_id=section)
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(prenoms__icontains=q) | Q(code__icontains=q))
    return qs


class Situation(AccesMixin, TemplateView):
    """Soldes de tous les producteurs : qui doit être payé, qui a une avance à rembourser."""

    model = Paiement
    template_name = "paiements/situation.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET
        campagne = Campagne.objects.filter(pk=g.get("campagne")).first() if g.get("campagne") else None
        qs = soldes_producteurs(campagne, g.get("section"), g.get("q", "").strip())
        filtre = g.get("filtre")
        if filtre == "a_payer":
            qs = qs.filter(solde__gt=0)
        elif filtre == "debiteurs":
            qs = qs.filter(solde__lt=0)
        else:
            qs = qs.exclude(total_achats=0, total_primes=0, total_paiements=0, total_avances=0)
        lignes = list(qs.order_by("-solde"))
        ctx.update(
            lignes=lignes,
            campagne=campagne,
            campagnes=Campagne.objects.all(),
            sections=Section.objects.all(),
            totaux={
                cle: sum(getattr(l, cle) for l in lignes)
                for cle in ("total_poids", "total_achats", "total_primes", "total_paiements", "total_avances",
                            "solde")
            },
        )
        return ctx


@login_required
@permission_required("paiements.view_paiement", raise_exception=True)
def export_situation(request):
    g = request.GET
    campagne = Campagne.objects.filter(pk=g.get("campagne")).first() if g.get("campagne") else None
    lignes = (
        [p.code, p.nom_complet, p.section or "", p.total_poids, p.total_achats, p.total_primes, p.total_paiements,
         p.total_avances, p.solde]
        for p in soldes_producteurs(campagne, g.get("section")).order_by("nom")
    )
    return reponse_csv(
        "situation_producteurs.csv",
        ["Code", "Producteur", "Section", "Poids net (kg)", "Achats", "Primes", "Paiements", "Avances", "Solde"],
        lignes,
    )


@login_required
@permission_required("paiements.view_paiement", raise_exception=True)
def recu(request, pk):
    paiement = get_object_or_404(Paiement.objects.select_related("producteur", "campagne"), pk=pk)
    return render(request, "paiements/recu.html", {
        "paiement": paiement,
        "situation": situation_producteur(paiement.producteur),
    })


@login_required
@permission_required("paiements.view_paiement", raise_exception=True)
def releve(request, pk):
    """Relevé de compte imprimable d'un producteur."""
    producteur = get_object_or_404(Producteur, pk=pk)
    campagne = Campagne.objects.filter(pk=request.GET.get("campagne")).first() if request.GET.get("campagne") else None
    filtre = {"campagne": campagne} if campagne else {}
    mouvements = []
    for a in producteur.achats.filter(**filtre):
        mouvements.append((a.date, f"Achat {a.numero} – {a.poids_net} kg à {a.prix_kg} F/kg", a.montant, 0))
    for p in producteur.primes.filter(**filtre):
        mouvements.append((p.date, p.get_type_prime_display(), p.montant, 0))
    for p in producteur.avances.filter(**filtre):
        mouvements.append((p.date, f"Avance {p.motif}".strip(), 0, p.montant))
    for p in producteur.paiements.filter(**filtre):
        mouvements.append((p.date, f"Paiement {p.numero} ({p.get_mode_display()})", 0, p.montant))
    mouvements.sort(key=lambda m: m[0])
    solde, lignes = 0, []
    for date, libelle, credit, debit in mouvements:
        solde += credit - debit
        lignes.append({"date": date, "libelle": libelle, "credit": credit, "debit": debit, "solde": solde})
    return render(request, "paiements/releve.html", {
        "producteur": producteur,
        "campagne": campagne,
        "lignes": lignes,
        "situation": situation_producteur(producteur, campagne),
    })
