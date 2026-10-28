from django.urls import path

from . import views

app_name = "achats"

urlpatterns = [
    path("", views.AchatListe.as_view(), name="liste"),
    path("nouveau/", views.AchatCreation.as_view(), name="creer"),
    path("export.csv", views.export_achats, name="export"),
    path("<int:pk>/", views.AchatDetail.as_view(), name="detail"),
    path("<int:pk>/recu/", views.recu, name="recu"),
    path("<int:pk>/modifier/", views.AchatModification.as_view(), name="modifier"),
    path("<int:pk>/supprimer/", views.AchatSuppression.as_view(), name="supprimer"),
]
