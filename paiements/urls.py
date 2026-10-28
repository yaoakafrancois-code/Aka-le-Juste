from django.urls import path

from . import views

app_name = "paiements"

urlpatterns = [
    path("", views.PaiementListe.as_view(), name="liste"),
    path("nouveau/", views.PaiementCreation.as_view(), name="creer"),
    path("<int:pk>/recu/", views.recu, name="recu"),
    path("<int:pk>/modifier/", views.PaiementModification.as_view(), name="modifier"),
    path("<int:pk>/supprimer/", views.PaiementSuppression.as_view(), name="supprimer"),
    path("avances/", views.AvanceListe.as_view(), name="avances"),
    path("avances/nouvelle/", views.AvanceCreation.as_view(), name="avance_creer"),
    path("avances/<int:pk>/modifier/", views.AvanceModification.as_view(), name="avance_modifier"),
    path("avances/<int:pk>/supprimer/", views.AvanceSuppression.as_view(), name="avance_supprimer"),
    path("primes/", views.PrimeListe.as_view(), name="primes"),
    path("primes/nouvelle/", views.PrimeCreation.as_view(), name="prime_creer"),
    path("primes/<int:pk>/modifier/", views.PrimeModification.as_view(), name="prime_modifier"),
    path("primes/<int:pk>/supprimer/", views.PrimeSuppression.as_view(), name="prime_supprimer"),
    path("situation/", views.Situation.as_view(), name="situation"),
    path("situation/export.csv", views.export_situation, name="situation_export"),
    path("releve/<int:pk>/", views.releve, name="releve"),
]
