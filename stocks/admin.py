from django.contrib import admin

from .models import Exportateur, LigneLot, Livraison, Lot


@admin.register(Exportateur)
class ExportateurAdmin(admin.ModelAdmin):
    list_display = ("nom", "numero_agrement", "code_ccc", "contact", "telephone")
    search_fields = ("nom",)


class LigneLotInline(admin.TabularInline):
    model = LigneLot
    extra = 0
    raw_id_fields = ("achat",)


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ("numero", "magasin", "campagne", "programme", "date_creation", "statut", "grade")
    list_filter = ("statut", "magasin", "campagne", "programme")
    inlines = [LigneLotInline]


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ("numero", "numero_connaissement", "date", "exportateur", "poids_livre", "prix_kg")
    list_filter = ("exportateur", "destination")
    search_fields = ("numero", "numero_connaissement", "immatriculation")
    filter_horizontal = ("lots",)
