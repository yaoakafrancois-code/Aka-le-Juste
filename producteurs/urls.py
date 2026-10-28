from django.urls import path

from . import views

app_name = "producteurs"

urlpatterns = [
    path("", views.ProducteurListe.as_view(), name="liste"),
    path("nouveau/", views.ProducteurCreation.as_view(), name="creer"),
    path("export.csv", views.export_producteurs, name="export"),
    path("<int:pk>/", views.ProducteurDetail.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.ProducteurModification.as_view(), name="modifier"),
    path("<int:pk>/supprimer/", views.ProducteurSuppression.as_view(), name="supprimer"),
    path("<int:pk>/parcelles.json", views.parcelles_json, name="parcelles_json"),
    path("parcelles/", views.ParcelleListe.as_view(), name="parcelles"),
    path("parcelles/nouvelle/", views.ParcelleCreation.as_view(), name="parcelle_creer"),
    path("parcelles/export.csv", views.export_parcelles, name="parcelles_export"),
    path("parcelles/<int:pk>/modifier/", views.ParcelleModification.as_view(), name="parcelle_modifier"),
    path("parcelles/<int:pk>/supprimer/", views.ParcelleSuppression.as_view(), name="parcelle_supprimer"),
]
