from django.urls import path

from . import installation, views

app_name = "core"

urlpatterns = [
    path("", views.tableau_de_bord, name="tableau_de_bord"),
    path("rapports/", views.rapports, name="rapports"),
    path("manifest.webmanifest", views.manifeste, name="manifeste"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("hors-ligne/", views.hors_ligne, name="hors_ligne"),
    path("installation/", installation.assistant, name="installation"),
]
