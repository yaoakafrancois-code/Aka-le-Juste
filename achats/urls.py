from django.urls import path

from . import terrain, views

app_name = "achats"

urlpatterns = [
    path("", views.AchatListe.as_view(), name="liste"),
    path("nouveau/", views.AchatCreation.as_view(), name="creer"),
    path("export.csv", views.export_achats, name="export"),
    path("terrain/", terrain.page, name="terrain"),
    path("terrain/donnees.json", terrain.donnees, name="terrain_donnees"),
    path("terrain/synchroniser/", terrain.synchroniser, name="terrain_synchroniser"),
    path("<int:pk>/", views.AchatDetail.as_view(), name="detail"),
    path("<int:pk>/recu/", views.recu, name="recu"),
    path("<int:pk>/modifier/", views.AchatModification.as_view(), name="modifier"),
    path("<int:pk>/supprimer/", views.AchatSuppression.as_view(), name="supprimer"),
]
