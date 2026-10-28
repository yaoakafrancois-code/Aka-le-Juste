from django.contrib import admin

from .models import Exportateur, Livraison, Lot


@admin.register(Exportateur)
class ExportateurAdmin(admin.ModelAdmin):
    list_display = ("nom", "numero_agrement", "contact", "telephone")
    search_fields = ("nom",)


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ("numero", "magasin", "campagne", "date_creation", "statut")
    list_filter = ("statut", "magasin", "campagne")


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ("numero", "date", "exportateur", "poids_livre", "prix_kg")
    list_filter = ("exportateur",)
    filter_horizontal = ("lots",)
