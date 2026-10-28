from core.models import Campagne
from core.vues import FormulaireStyle

from .models import CertificationProducteur, Parcelle, Producteur


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
            "annee_creation", "nombre_plants", "certifiee", "statut_eudr",
        ]


class CertificationForm(FormulaireStyle):
    class Meta:
        model = CertificationProducteur
        fields = [
            "producteur", "programme", "campagne", "statut", "niveau", "numero_membre", "superficie_certifiee_ha",
            "production_estimee_kg", "date_inspection_interne", "date_audit", "observations",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["campagne"].initial = Campagne.objects.active()
