from django import forms
from django.core.exceptions import ValidationError

from core.models import Campagne
from core.vues import FormulaireStyle
from producteurs.models import Programme

from .models import Livraison, Lot


class LotForm(FormulaireStyle):
    class Meta:
        model = Lot
        fields = ["magasin", "campagne", "programme", "date_creation", "observations"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["programme"].queryset = Programme.objects.filter(actif=True)
        self.fields["programme"].empty_label = "Conventionnel (non certifié)"
        if not self.instance.pk:
            self.fields["campagne"].initial = Campagne.objects.active()
        elif self.instance.lignes.exists():
            # Le contenu du lot dépend du magasin, de la campagne et du programme.
            for nom in ("magasin", "campagne", "programme"):
                self.fields[nom].disabled = True


class AnalyseQualiteForm(FormulaireStyle):
    class Meta:
        model = Lot
        fields = ["date_analyse", "humidite", "grainage", "taux_moisi", "taux_ardoise", "taux_defauts", "grade"]


class LivraisonForm(FormulaireStyle):
    class Meta:
        model = Livraison
        fields = [
            "date", "exportateur", "lots", "numero_connaissement", "destination", "adresse_destination",
            "nombre_sacs", "poids_brut", "poids_livre", "prix_kg", "transporteur", "immatriculation",
            "immatriculation_remorque", "chauffeur", "permis_chauffeur", "telephone_chauffeur",
            "poids_reconnu", "numero_ticket_pesee", "observations",
        ]
        widgets = {"lots": forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lots = Lot.objects.filter(statut="ferme")
        if self.instance.pk:
            lots = lots | self.instance.lots.all()
        self.fields["lots"].queryset = lots.distinct().select_related("magasin", "programme")
        self.fields["lots"].label_from_instance = lambda lot: (
            f"{lot.numero} – {lot.magasin.nom} – {lot.type_produit} – {lot.poids_net:,.0f} kg".replace(",", " ")
        )
        self.fields["lots"].help_text = (
            "Seuls les lots fermés sont proposés. Un connaissement ne mélange pas certifié et conventionnel."
        )

    def clean_poids_livre(self):
        poids = self.cleaned_data["poids_livre"]
        if poids <= 0:
            raise forms.ValidationError("Le poids livré doit être positif.")
        return poids

    def clean_lots(self):
        lots = self.cleaned_data["lots"]
        try:
            Livraison.verifier_lots(lots)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return lots
