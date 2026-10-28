from django import forms

from core.models import Campagne
from core.vues import FormulaireStyle

from .models import Avance, Paiement, Prime, situation_producteur


class AvecCampagneActive(FormulaireStyle):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["campagne"].initial = Campagne.objects.active()


class PaiementForm(AvecCampagneActive):
    class Meta:
        model = Paiement
        fields = ["date", "campagne", "producteur", "montant", "mode", "reference", "observations"]

    def clean(self):
        donnees = super().clean()
        producteur, montant = donnees.get("producteur"), donnees.get("montant")
        if producteur and montant is not None:
            if montant <= 0:
                self.add_error("montant", "Le montant doit être positif.")
            solde = situation_producteur(producteur)["solde"]
            if self.instance.pk and self.instance.producteur_id == producteur.pk:
                solde += self.instance.montant
            if montant > solde:
                self.add_error(
                    "montant",
                    "Le montant dépasse le solde dû au producteur ({} FCFA). "
                    "Pour un pré-financement, enregistrez une avance.".format(f"{solde:,.0f}".replace(",", " ")),
                )
        return donnees


class AvanceForm(AvecCampagneActive):
    class Meta:
        model = Avance
        fields = ["date", "campagne", "producteur", "montant", "mode", "motif"]

    def clean_montant(self):
        montant = self.cleaned_data["montant"]
        if montant <= 0:
            raise forms.ValidationError("Le montant doit être positif.")
        return montant


class PrimeForm(AvecCampagneActive):
    class Meta:
        model = Prime
        fields = ["date", "campagne", "producteur", "type_prime", "montant", "observations"]

    def clean_montant(self):
        montant = self.cleaned_data["montant"]
        if montant <= 0:
            raise forms.ValidationError("Le montant doit être positif.")
        return montant
