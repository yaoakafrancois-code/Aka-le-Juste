from django.utils import timezone

from .models import Campagne, Cooperative


def cooperative(request):
    campagne = Campagne.objects.active()
    return {
        "cooperative": Cooperative.courante(),
        "campagne_active": campagne,
        "prix_du_jour": campagne.prix_applicable(timezone.localdate()) if campagne else None,
    }
