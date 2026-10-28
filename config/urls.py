from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

admin.site.site_header = "CacaoCoop – Paramètres"
admin.site.site_title = "CacaoCoop"
admin.site.index_title = "Paramètres et administration"

urlpatterns = [
    path("", include("core.urls")),
    path("producteurs/", include("producteurs.urls")),
    path("achats/", include("achats.urls")),
    path("paiements/", include("paiements.urls")),
    path("stocks/", include("stocks.urls")),
    path("connexion/", auth_views.LoginView.as_view(), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("parametres/", admin.site.urls),
]
