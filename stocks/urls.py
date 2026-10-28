from django.urls import path

from . import views

app_name = "stocks"

urlpatterns = [
    path("", views.Stock.as_view(), name="stock"),
    path("lots/", views.LotListe.as_view(), name="lots"),
    path("lots/nouveau/", views.LotCreation.as_view(), name="lot_creer"),
    path("lots/<int:pk>/", views.LotDetail.as_view(), name="lot_detail"),
    path("lots/<int:pk>/modifier/", views.LotModification.as_view(), name="lot_modifier"),
    path("lots/<int:pk>/supprimer/", views.LotSuppression.as_view(), name="lot_supprimer"),
    path("lots/<int:pk>/achats/", views.lot_achats, name="lot_achats"),
    path("lots/<int:pk>/statut/", views.lot_statut, name="lot_statut"),
    path("lots/<int:pk>/tracabilite.csv", views.lot_tracabilite, name="lot_tracabilite"),
    path("livraisons/", views.LivraisonListe.as_view(), name="livraisons"),
    path("livraisons/nouvelle/", views.LivraisonCreation.as_view(), name="livraison_creer"),
    path("livraisons/<int:pk>/", views.LivraisonDetail.as_view(), name="livraison_detail"),
    path("livraisons/<int:pk>/modifier/", views.LivraisonModification.as_view(), name="livraison_modifier"),
    path("livraisons/<int:pk>/supprimer/", views.LivraisonSuppression.as_view(), name="livraison_supprimer"),
]
