from django import forms

from core.models import Campagne
from core.vues import FormulaireStyle
from producteurs.models import Parcelle, Producteur
from stocks.models import Lot

from .models import Achat


class AchatForm(FormulaireStyle):
    class Meta:
        model = Achat
        fields = [
            "date", "campagne", "magasin", "producteur", "parcelle", "nombre_sacs", "poids_brut", "tare",
            "humidite", "refaction", "qualite", "prix_kg", "lot", "observations",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["prix_kg"].required = False
        self.fields["producteur"].queryset = Producteur.objects.filter(actif=True)
        self.fields["lot"].queryset = Lot.objects.filter(statut="ouvert").select_related("magasin")
        if not self.instance.pk:
            self.fields["campagne"].initial = Campagne.objects.active()
        # Limiter les parcelles à celles du producteur choisi.
        producteur_id = self.data.get("producteur") or self.initial.get("producteur") or self.instance.producteur_id
        if producteur_id:
            self.fields["parcelle"].queryset = Parcelle.objects.filter(producteur_id=producteur_id)
        else:
            self.fields["parcelle"].queryset = Parcelle.objects.none()
        for nom in ("poids_brut", "tare", "refaction", "prix_kg"):
            self.fields[nom].widget.attrs["data-calcul"] = "1"

    def clean(self):
        donnees = super().clean()
        if self.instance.pk and self.instance.lot_id and self.instance.lot.statut == "livre":
            raise forms.ValidationError("Cet achat fait partie d'un lot déjà livré : il ne peut plus être modifié.")
        if donnees.get("prix_kg") is None and donnees.get("campagne"):
            donnees["prix_kg"] = donnees["campagne"].prix_kg
            self.instance.prix_kg = donnees["prix_kg"]
        return donnees


class FiltreAchatForm(forms.Form):
    du = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    au = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
