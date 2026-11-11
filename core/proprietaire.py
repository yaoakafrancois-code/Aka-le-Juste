"""Vue du propriétaire : un résumé simple, lisible sur téléphone.

- Si le logiciel est sur un serveur internet, le propriétaire se connecte et ouvre cette page.
- Si le logiciel est au bureau sans internet permanent, le magasinier clique sur « Envoyer au propriétaire »
  quand la connexion est là : le résumé part vers le serveur Akagri, et le propriétaire le lit avec son lien privé.
"""

import json
import urllib.error
import urllib.request
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from achats.models import Achat
from paiements.models import Avance, Paiement, Prime
from stocks.models import Livraison, stock_par_magasin

from .models import Campagne, Cooperative, ResumeRecu

TAILLE_MAX = 200_000  # octets


def _somme(qs, champ="montant"):
    return qs.aggregate(t=Sum(champ))["t"] or 0


def _periode(achats):
    return {"poids": _somme(achats, "poids_net"), "montant": _somme(achats), "pesees": achats.count()}


def construire_resume():
    """Chiffres clés de la campagne active, sous forme de dictionnaire simple (nombres et textes)."""
    coop = Cooperative.courante()
    campagne = Campagne.objects.active()
    filtre = {"campagne": campagne} if campagne else {}
    achats = Achat.objects.filter(**filtre)
    aujourd_hui = timezone.localdate()
    total_achats = _somme(achats)
    primes = _somme(Prime.objects.filter(**filtre)) + _somme(achats, "montant_prime")
    paye = _somme(Paiement.objects.filter(**filtre))
    avances = _somme(Avance.objects.filter(**filtre))
    livraisons = Livraison.objects.filter(lots__campagne=campagne).distinct() if campagne else Livraison.objects.all()
    stock = stock_par_magasin(campagne)
    resume = {
        "structure": str(coop.nom),
        "produit": coop.infos_produit["titre"],
        "campagne": str(campagne) if campagne else "",
        "genere_le": timezone.localtime().strftime("%d/%m/%Y à %H:%M"),
        "jour": _periode(achats.filter(date=aujourd_hui)),
        "semaine": _periode(achats.filter(date__gt=aujourd_hui - timedelta(days=7))),
        "total": _periode(achats),
        "par_produit": [
            {"nom": nom, "poids": _somme(achats.filter(produit=code), "poids_net"),
             "montant": _somme(achats.filter(produit=code)),
             "stock_kg": sum(p["poids"] for l in stock for p in l["par_produit"] if p["code"] == code)}
            for code, nom in coop.choix_produits
        ] if len(coop.codes_produits) > 1 else [],
        "primes": primes,
        "paye": paye,
        "avances": avances,
        "reste_a_payer": total_achats + primes - paye - avances,
        "stock_total": sum(l["poids"] for l in stock),
        "stock": [{"magasin": l["magasin"].nom, "poids": l["poids"]} for l in stock],
        "livre": _somme(livraisons, "poids_livre"),
        "dernieres": [
            {"date": a.date.strftime("%d/%m"), "producteur": a.producteur.nom_complet, "magasin": a.magasin.nom,
             "produit": a.get_produit_display(),
             "poids": a.poids_net, "montant": a.montant}
            for a in achats.select_related("producteur", "magasin")[:10]
        ],
    }
    # Aller-retour JSON : exactement la même forme que le résumé reçu par internet.
    return json.loads(json.dumps(resume, cls=DjangoJSONEncoder))


NOMBRES = {"stock_kg", "poids", "montant", "pesees", "primes", "paye", "avances", "reste_a_payer", "stock_total", "livre"}


def _nombres(valeur, cle=None):
    """Les montants voyagent en texte (décimaux) : on les remet en nombres pour l'affichage."""
    if isinstance(valeur, dict):
        return {k: _nombres(v, k) for k, v in valeur.items()}
    if isinstance(valeur, list):
        return [_nombres(v) for v in valeur]
    if cle in NOMBRES:
        try:
            return float(valeur)
        except (TypeError, ValueError):
            return 0
    return valeur


def _lien_prive(request, coop):
    base = (coop.url_relais or request.build_absolute_uri("/")).rstrip("/")
    return f"{base}/p/{coop.cle_relais}/"


@login_required
def proprietaire(request):
    coop = Cooperative.courante()
    return render(request, "core/proprietaire.html", {
        "r": _nombres(construire_resume()), "local": True, "relais": bool(coop.url_relais),
        "lien_prive": _lien_prive(request, coop) if coop.pk and coop.url_relais else "",
        "cle": coop.cle_relais if coop.pk else "",
    })


@login_required
@require_POST
def envoyer(request):
    """Envoie le résumé au serveur Akagri (à faire quand internet est disponible)."""
    coop = Cooperative.courante()
    if not coop.pk or not coop.url_relais:
        messages.error(request, "Aucune adresse de serveur : renseignez-la dans Paramètres > Coopérative.")
        return redirect("core:proprietaire")
    corps = json.dumps({"cle": coop.cle_relais, "donnees": construire_resume()}).encode()
    requete = urllib.request.Request(
        coop.url_relais.rstrip("/") + "/relais/recevoir/", data=corps,
        headers={"Content-Type": "application/json", "User-Agent": "Akagri"}, method="POST",
    )
    try:
        with urllib.request.urlopen(requete, timeout=20) as reponse:
            ok = reponse.status == 200
    except urllib.error.HTTPError as e:
        ok = False
        if e.code == 403:
            messages.error(request, "Envoi refusé : l'abonnement à la vue du propriétaire n'est pas actif. "
                                    "Contactez votre fournisseur Akagri.")
            return redirect("core:proprietaire")
    except (urllib.error.URLError, OSError):
        messages.error(request, "Pas de connexion internet (ou serveur injoignable). Réessayez quand le réseau "
                                "est revenu : rien n'est perdu.")
        return redirect("core:proprietaire")
    if ok:
        messages.success(request, "Résumé envoyé. Le propriétaire peut le voir sur son téléphone.")
    else:
        messages.error(request, "Le serveur n'a pas accepté l'envoi. Réessayez plus tard.")
    return redirect("core:proprietaire")


@csrf_exempt
@require_POST
def recevoir(request):
    """Côté serveur : reçoit le résumé d'un bureau abonné (clé connue et active uniquement)."""
    if len(request.body) > TAILLE_MAX:
        return JsonResponse({"erreur": "trop volumineux"}, status=413)
    try:
        contenu = json.loads(request.body)
        cle, donnees = contenu["cle"], contenu["donnees"]
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"erreur": "format"}, status=400)
    if not isinstance(cle, str) or not isinstance(donnees, dict):
        return JsonResponse({"erreur": "format"}, status=400)
    abonne = ResumeRecu.objects.filter(cle=cle, actif=True).first()
    if abonne is None:
        return JsonResponse({"erreur": "abonnement inactif"}, status=403)
    abonne.donnees = donnees
    abonne.recu_le = timezone.now()
    abonne.save(update_fields=["donnees", "recu_le"])
    return JsonResponse({"ok": True})


def vue_privee(request, cle):
    """Page du propriétaire, ouverte avec son lien privé (sans mot de passe)."""
    abonne = ResumeRecu.objects.filter(cle=cle, actif=True).first()
    if abonne is None or not abonne.donnees:
        raise Http404("Lien inconnu ou aucun résumé reçu pour le moment.")
    reponse = render(request, "core/proprietaire.html", {"r": _nombres(abonne.donnees), "local": False,
                                                         "recu_le": abonne.recu_le})
    reponse["X-Robots-Tag"] = "noindex, nofollow"
    reponse["Cache-Control"] = "no-store"
    return reponse
