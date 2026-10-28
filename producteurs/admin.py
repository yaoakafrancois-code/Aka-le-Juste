from django.contrib import admin

from .models import AugmentationQuota, CertificationProducteur, Parcelle, Producteur, Programme


class ParcelleInline(admin.TabularInline):
    model = Parcelle
    extra = 0


class CertificationInline(admin.TabularInline):
    model = CertificationProducteur
    extra = 0


@admin.register(Producteur)
class ProducteurAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "prenoms", "section", "village", "telephone", "actif")
    list_filter = ("section", "actif", "sexe")
    search_fields = ("code", "nom", "prenoms", "telephone")
    inlines = [ParcelleInline, CertificationInline]


@admin.register(Parcelle)
class ParcelleAdmin(admin.ModelAdmin):
    list_display = ("code", "producteur", "superficie_ha", "certifiee", "statut_eudr")
    list_filter = ("certifiee", "statut_eudr")
    search_fields = ("code", "producteur__nom", "producteur__code")


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "rendement_reference_kg_ha", "rendement_max_kg_ha", "prime_kg", "numero_certificat",
                    "actif")


@admin.register(CertificationProducteur)
class CertificationProducteurAdmin(admin.ModelAdmin):
    list_display = ("producteur", "programme", "campagne", "statut", "niveau", "production_estimee_kg")
    list_filter = ("programme", "campagne", "statut", "niveau")
    search_fields = ("producteur__nom", "producteur__code", "numero_membre")
    raw_id_fields = ("producteur",)


@admin.register(AugmentationQuota)
class AugmentationQuotaAdmin(admin.ModelAdmin):
    list_display = ("certification", "quantite_kg", "motif", "statut", "demande_par", "decide_par", "demande_le")
    list_filter = ("statut", "motif")
    readonly_fields = ("statut", "demande_par", "decide_par", "decide_le")
    raw_id_fields = ("certification",)
