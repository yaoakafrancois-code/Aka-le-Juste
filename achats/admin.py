from django.contrib import admin

from .models import Achat


@admin.register(Achat)
class AchatAdmin(admin.ModelAdmin):
    list_display = ("numero", "date", "producteur", "magasin", "poids_net", "poids_certifie", "programme",
                    "prix_kg", "montant", "montant_prime")
    list_filter = ("campagne", "magasin", "programme", "qualite")
    search_fields = ("numero", "producteur__nom", "producteur__code")
    date_hierarchy = "date"
    readonly_fields = ("poids_net", "poids_certifie", "poids_non_certifie", "montant", "montant_prime", "source_prix")
