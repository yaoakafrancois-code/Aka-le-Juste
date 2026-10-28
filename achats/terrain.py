"""Collecte terrain : saisie des pesées sur tablette ou téléphone, y compris sans connexion.

La tablette télécharge les données utiles (producteurs, cartes, quotas, magasins, prix), enregistre les
pesées localement, puis les envoie au serveur dès que la connexion revient. Chaque pesée porte un
identifiant unique : l'envoyer deux fois ne crée jamais de doublon.
"""

import json

from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Campagne, Magasin
from producteurs.models import CertificationProducteur, Producteur

from .forms import AchatForm
from .models import Achat


@login_required
@permission_required("achats.add_achat", raise_exception=True)
def page(request):
    return render(request, "achats/terrain.html")


@login_required
@permission_required("achats.add_achat", raise_exception=True)
def donnees(request):
    campagne = Campagne.objects.active()
    if campagne is None:
        return JsonResponse({"erreur": "Aucune campagne active."}, status=400)
    aujourd_hui = timezone.localdate()
    certifications = {}
    for c in CertificationProducteur.objects.filter(campagne=campagne).select_related("programme", "producteur"):
        certifications.setdefault(c.producteur_id, []).append({
            "programme": c.programme_id, "code": c.programme.code, "certifie": c.statut == "certifie",
            "statut": c.get_statut_display(), "quota": float(c.quota_kg), "restant": float(c.volume_restant()),
            "prime_kg": float(c.programme.prime_kg), "explication": c.explication_quota,
        })
    producteurs = [
        {
            "id": p.pk, "code": p.code, "nom": p.nom_complet, "carte": p.numero_carte_ccc,
            "village": p.village, "section": str(p.section or ""), "superficie": float(p.superficie_totale),
            "parcelles": [{"id": pa.pk, "libelle": str(pa)} for pa in p.parcelles.all()],
            "certifications": certifications.get(p.pk, []),
        }
        for p in Producteur.objects.filter(actif=True).select_related("section").prefetch_related("parcelles")
    ]
    return JsonResponse({
        "genere_le": timezone.now().isoformat(),
        "date": aujourd_hui.isoformat(),
        "campagne": {"id": campagne.pk, "libelle": str(campagne)},
        "magasins": [
            {"id": m.pk, "nom": str(m), "prix_kg": float(campagne.prix_applicable(aujourd_hui, m))}
            for m in Magasin.objects.all()
        ],
        "producteurs": producteurs,
        "utilisateur": request.user.get_username(),
    })


@require_POST
@login_required
@permission_required("achats.add_achat", raise_exception=True)
def synchroniser(request):
    """Reçoit une pesée saisie sur le terrain. Réponse : le n° de reçu définitif, ou les erreurs."""
    try:
        saisie = json.loads(request.body)
    except ValueError:
        return JsonResponse({"statut": "erreur", "erreurs": ["Données illisibles."]}, status=400)
    reference = str(saisie.get("reference", ""))[:40]
    if not reference:
        return JsonResponse({"statut": "erreur", "erreurs": ["Référence manquante."]}, status=400)

    existant = Achat.objects.filter(reference_terrain=reference).first()
    if existant:
        return JsonResponse(resultat(existant, deja=True))

    champs = ("date", "campagne", "magasin", "producteur", "parcelle", "nombre_sacs", "poids_brut", "tare",
              "humidite", "refaction", "qualite", "observations")
    form = AchatForm(data={k: saisie.get(k) if saisie.get(k) is not None else "" for k in champs})
    if not form.is_valid():
        erreurs = [f"{form.fields[c].label if c in form.fields else ''} : {' '.join(m)}".strip(" :")
                   for c, m in form.errors.items()]
        return JsonResponse({"statut": "erreur", "erreurs": erreurs}, status=422)
    achat = form.save(commit=False)
    achat.reference_terrain = reference
    achat.agent = request.user
    try:
        with transaction.atomic():
            achat.save()
    except IntegrityError:  # même pesée envoyée deux fois au même instant
        achat = Achat.objects.get(reference_terrain=reference)
        return JsonResponse(resultat(achat, deja=True))
    return JsonResponse(resultat(achat))


def resultat(achat, deja=False):
    return {
        "statut": "deja" if deja else "ok",
        "numero": achat.numero,
        "url_recu": reverse("achats:recu", args=[achat.pk]),
        "poids_net": float(achat.poids_net),
        "poids_certifie": float(achat.poids_certifie),
        "poids_non_certifie": float(achat.poids_non_certifie),
        "montant_total": float(achat.montant_total),
    }
