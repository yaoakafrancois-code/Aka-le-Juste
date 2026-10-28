from core.vues import FormulaireStyle

from .models import Parcelle, Producteur


class ProducteurForm(FormulaireStyle):
    class Meta:
        model = Producteur
        fields = [
            "code", "nom", "prenoms", "sexe", "date_naissance", "telephone", "numero_piece",
            "numero_carte_ccc", "section", "village", "date_adhesion", "actif",
        ]


class ParcelleForm(FormulaireStyle):
    class Meta:
        model = Parcelle
        fields = [
            "producteur", "code", "localite", "superficie_ha", "latitude", "longitude", "polygone_geojson",
            "annee_creation", "nombre_plants", "certification", "statut_eudr",
        ]
