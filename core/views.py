from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render

from achats.models import Achat
from paiements.models import Avance, Paiement, Prime
from producteurs.models import Parcelle, Producteur
from stocks.models import Livraison, stock_par_magasin

from .models import Campagne


def _campagne_demandee(request):
    if request.GET.get("campagne"):
        return Campagne.objects.filter(pk=request.GET["campagne"]).first()
    return Campagne.objects.active()


def _somme(qs, champ="montant"):
    return qs.aggregate(t=Sum(champ))["t"] or 0


@login_required
def tableau_de_bord(request):
    campagne = _campagne_demandee(request)
    filtre = {"campagne": campagne} if campagne else {}
    achats = Achat.objects.filter(**filtre)
    total_achats = _somme(achats)
    total_primes = _somme(Prime.objects.filter(**filtre))
    total_paiements = _somme(Paiement.objects.filter(**filtre))
    total_avances = _somme(Avance.objects.filter(**filtre))
    livraisons = Livraison.objects.filter(lots__campagne=campagne).distinct() if campagne else Livraison.objects.all()
    par_mois = list(
        achats.annotate(mois=TruncMonth("date")).values("mois")
        .annotate(poids=Sum("poids_net"), montant=Sum("montant")).order_by("mois")
    )
    poids_max = max((m["poids"] for m in par_mois), default=0) or 1
    for m in par_mois:
        m["pourcentage"] = float(m["poids"] / poids_max * 100)
    stock = stock_par_magasin(campagne)
    contexte = {
        "campagne": campagne,
        "campagnes": Campagne.objects.all(),
        "nb_producteurs": Producteur.objects.filter(actif=True).count(),
        "nb_producteurs_livreurs": achats.values("producteur").distinct().count(),
        "nb_parcelles": Parcelle.objects.count(),
        "superficie": _somme(Parcelle.objects.all(), "superficie_ha"),
        "parcelles_geolocalisees": Parcelle.objects.filter(latitude__isnull=False, longitude__isnull=False).count(),
        "tonnage": _somme(achats, "poids_net"),
        "nb_achats": achats.count(),
        "total_achats": total_achats,
        "total_primes": total_primes,
        "total_paiements": total_paiements,
        "total_avances": total_avances,
        "reste_a_payer": total_achats + total_primes - total_paiements - total_avances,
        "poids_livre": _somme(livraisons, "poids_livre"),
        "stock": stock,
        "stock_total": sum(l["poids"] for l in stock),
        "par_mois": par_mois,
        "derniers_achats": achats.select_related("producteur", "magasin")[:8],
    }
    return render(request, "core/tableau_de_bord.html", contexte)


@login_required
def rapports(request):
    campagne = _campagne_demandee(request)
    filtre = {"campagne": campagne} if campagne else {}
    achats = Achat.objects.filter(**filtre)
    agreger = dict(poids=Sum("poids_net"), montant=Sum("montant"), sacs=Sum("nombre_sacs"), nombre=Count("id"),
                   producteurs=Count("producteur", distinct=True))
    contexte = {
        "campagne": campagne,
        "campagnes": Campagne.objects.all(),
        "par_section": achats.values("producteur__section__nom").annotate(**agreger).order_by("-poids"),
        "par_magasin": achats.values("magasin__code", "magasin__nom").annotate(**agreger).order_by("-poids"),
        "par_qualite": achats.values("qualite").annotate(**agreger).order_by("-poids"),
        "par_mois": achats.annotate(mois=TruncMonth("date")).values("mois").annotate(**agreger).order_by("mois"),
        "top_producteurs": achats.values("producteur__id", "producteur__code", "producteur__nom",
                                         "producteur__prenoms").annotate(**agreger).order_by("-poids")[:20],
        "qualites": dict(Achat.QUALITE_CHOICES),
        "total": achats.aggregate(**agreger),
    }
    return render(request, "core/rapports.html", contexte)
