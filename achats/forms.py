from django import forms

from core.models import Campagne
from core.vues import FormulaireStyle
from producteurs.models import Parcelle, Producteur, Programme

from .models import Achat


class AchatForm(FormulaireStyle):
    class Meta:
        model = Achat
        fields = [
            "date", "campagne", "magasin", "producteur", "parcelle", "nombre_sacs", "poids_brut", "tare",
            "humidite", "refaction", "qualite", "prix_kg", "programme", "vendre_non_certifie", "observations",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["prix_kg"].required = False
        self.fields["programme"].queryset = Programme.objects.filter(actif=True)
        self.fields["programme"].empty_label = "Automatique (selon la certification du producteur)"
        self.fields["producteur"].queryset = Producteur.objects.filter(actif=True)
        if not self.instance.pk:
            self.fields["campagne"].initial = Campagne.objects.active()
        # Limiter les parcelles à celles du producteur choisi.
        producteur_id = self.data.get("producteur") or self.initial.get("producteur") or self.instance.producteur_id
        if producteur_id:
            self.fields["parcelle"].queryset = Parcelle.objects.filter(producteur_id=producteur_id)
        else:
            self.fields["parcelle"].queryset = Parcelle.objects.none()

    def clean(self):
        donnees = super().clean()
        if self.instance.pk and self.instance.lignes_lot.exists():
            raise forms.ValidationError(
                "Cet achat est déjà placé dans un lot : retirez-le du lot avant de le modifier."
            )
        return donnees
