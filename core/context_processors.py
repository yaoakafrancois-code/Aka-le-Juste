from django.utils import timezone

from .models import Campagne, Cooperative


def cooperative(request):
    campagne = Campagne.objects.active()
    coop = Cooperative.courante()
    return {
        "cooperative": coop,
        "est_cacao": coop.est_cacao,
        "produit": coop.infos_produit,
        "campagne_active": campagne,
        "prix_du_jour": campagne.prix_applicable(timezone.localdate()) if campagne else None,
    }
