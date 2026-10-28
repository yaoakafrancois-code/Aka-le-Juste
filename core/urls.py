from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.tableau_de_bord, name="tableau_de_bord"),
    path("rapports/", views.rapports, name="rapports"),
]
