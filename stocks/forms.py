from django import forms

from core.models import Campagne
from core.vues import FormulaireStyle

from .models import Livraison, Lot


class LotForm(FormulaireStyle):
    class Meta:
        model = Lot
        fields = ["magasin", "campagne", "date_creation", "observations"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["campagne"].initial = Campagne.objects.active()
        else:
            # Changer de magasin rendrait les achats du lot incohérents.
            self.fields["magasin"].disabled = True


class LivraisonForm(FormulaireStyle):
    class Meta:
        model = Livraison
        fields = [
            "date", "exportateur", "lots", "poids_livre", "prix_kg", "transporteur", "immatriculation",
            "numero_bordereau", "observations",
        ]
        widgets = {"lots": forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lots = Lot.objects.filter(statut="ferme")
        if self.instance.pk:
            lots = lots | self.instance.lots.all()
        self.fields["lots"].queryset = lots.distinct().select_related("magasin")
        self.fields["lots"].label_from_instance = lambda lot: (
            f"{lot.numero} – {lot.magasin.nom} – {lot.poids_net:,.0f} kg".replace(",", " ")
        )
        self.fields["lots"].help_text = "Seuls les lots fermés (prêts à livrer) sont proposés."

    def clean_poids_livre(self):
        poids = self.cleaned_data["poids_livre"]
        if poids <= 0:
            raise forms.ValidationError("Le poids livré doit être positif.")
        return poids
