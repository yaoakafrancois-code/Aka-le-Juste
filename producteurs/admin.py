from django.contrib import admin

from .models import Parcelle, Producteur


class ParcelleInline(admin.TabularInline):
    model = Parcelle
    extra = 0


@admin.register(Producteur)
class ProducteurAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "prenoms", "section", "village", "telephone", "actif")
    list_filter = ("section", "actif", "sexe")
    search_fields = ("code", "nom", "prenoms", "telephone")
    inlines = [ParcelleInline]


@admin.register(Parcelle)
class ParcelleAdmin(admin.ModelAdmin):
    list_display = ("code", "producteur", "superficie_ha", "certification", "statut_eudr")
    list_filter = ("certification", "statut_eudr")
    search_fields = ("code", "producteur__nom", "producteur__code")
