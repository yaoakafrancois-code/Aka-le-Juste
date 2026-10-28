from django.contrib import admin

from .models import Avance, Paiement, Prime


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("numero", "date", "producteur", "montant", "mode", "reference")
    list_filter = ("campagne", "mode")
    search_fields = ("numero", "producteur__nom", "producteur__code", "reference")


@admin.register(Avance)
class AvanceAdmin(admin.ModelAdmin):
    list_display = ("date", "producteur", "montant", "mode", "motif")
    list_filter = ("campagne", "mode")
    search_fields = ("producteur__nom", "producteur__code")


@admin.register(Prime)
class PrimeAdmin(admin.ModelAdmin):
    list_display = ("date", "producteur", "type_prime", "montant")
    list_filter = ("campagne", "type_prime")
    search_fields = ("producteur__nom", "producteur__code")
