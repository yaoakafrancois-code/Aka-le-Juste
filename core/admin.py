from django.contrib import admin

from .models import Campagne, Cooperative, Magasin, PrixDuJour, Section


@admin.register(Cooperative)
class CooperativeAdmin(admin.ModelAdmin):
    list_display = ("nom", "sigle", "numero_agrement", "telephone")

    def has_add_permission(self, request):
        return not Cooperative.objects.exists()


class PrixDuJourInline(admin.TabularInline):
    model = PrixDuJour
    extra = 1


@admin.register(Campagne)
class CampagneAdmin(admin.ModelAdmin):
    list_display = ("libelle", "date_debut", "date_fin", "prix_kg", "active")
    list_editable = ("active",)
    inlines = [PrixDuJourInline]


@admin.register(PrixDuJour)
class PrixDuJourAdmin(admin.ModelAdmin):
    list_display = ("date", "campagne", "magasin", "prix_kg")
    list_filter = ("campagne", "magasin")
    date_hierarchy = "date"


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("nom", "localite", "delegue")
    search_fields = ("nom", "localite")


@admin.register(Magasin)
class MagasinAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "localite", "responsable", "capacite_kg")
    search_fields = ("code", "nom")
