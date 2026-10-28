from .models import Campagne, Cooperative


def cooperative(request):
    return {
        "cooperative": Cooperative.courante(),
        "campagne_active": Campagne.objects.active(),
    }
