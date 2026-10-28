from django.contrib import admin

from .models import Achat


@admin.register(Achat)
class AchatAdmin(admin.ModelAdmin):
    list_display = ("numero", "date", "producteur", "magasin", "poids_net", "prix_kg", "montant", "lot")
    list_filter = ("campagne", "magasin", "qualite")
    search_fields = ("numero", "producteur__nom", "producteur__code")
    date_hierarchy = "date"
    readonly_fields = ("poids_net", "montant")
