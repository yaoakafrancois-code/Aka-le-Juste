from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.models import Campagne, Magasin
from producteurs.models import Parcelle, Producteur

DEUX = Decimal("0.01")


class Achat(models.Model):
    """Achat (pesée) de fèves de cacao auprès d'un producteur."""

    QUALITE_CHOICES = [
        ("grade1", "Grade I"),
        ("grade2", "Grade II"),
        ("hors_standard", "Hors standard"),
    ]

    numero = models.CharField("n° de reçu", max_length=30, unique=True, blank=True)
    date = models.DateField(default=timezone.localdate)
    campagne = models.ForeignKey(Campagne, on_delete=models.PROTECT, related_name="achats")
    producteur = models.ForeignKey(Producteur, on_delete=models.PROTECT, related_name="achats")
    parcelle = models.ForeignKey(
        Parcelle, on_delete=models.SET_NULL, null=True, blank=True, related_name="achats",
        help_text="Parcelle d'origine (traçabilité).",
    )
    magasin = models.ForeignKey(Magasin, on_delete=models.PROTECT, related_name="achats")
    nombre_sacs = models.PositiveIntegerField("nombre de sacs", default=1)
    poids_brut = models.DecimalField("poids brut (kg)", max_digits=10, decimal_places=2)
    tare = models.DecimalField("tare (kg)", max_digits=8, decimal_places=2, default=Decimal("0"),
                               help_text="Poids des sacs vides.")
    humidite = models.DecimalField("humidité (%)", max_digits=5, decimal_places=2, null=True, blank=True)
    refaction = models.DecimalField(
        "réfaction (%)", max_digits=5, decimal_places=2, default=Decimal("0"),
        help_text="Déduction sur le poids pour humidité ou défauts.",
    )
    qualite = models.CharField("qualité", max_length=20, choices=QUALITE_CHOICES, default="grade1")
    prix_kg = models.DecimalField("prix (FCFA/kg)", max_digits=10, decimal_places=2, blank=True,
                                  help_text="Par défaut : prix de la campagne.")
    poids_net = models.DecimalField("poids net (kg)", max_digits=10, decimal_places=2, editable=False)
    montant = models.DecimalField("montant (FCFA)", max_digits=14, decimal_places=2, editable=False)
    lot = models.ForeignKey("stocks.Lot", on_delete=models.SET_NULL, null=True, blank=True, related_name="achats")
    observations = models.TextField(blank=True)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="achats_saisis")
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.numero} – {self.producteur.nom_complet}"

    def get_absolute_url(self):
        return reverse("achats:detail", args=[self.pk])

    @staticmethod
    def calculer_poids_net(poids_brut, tare, refaction):
        net = (Decimal(poids_brut) - Decimal(tare or 0)) * (1 - Decimal(refaction or 0) / 100)
        return net.quantize(DEUX, rounding=ROUND_HALF_UP)

    def clean(self):
        erreurs = {}
        if self.poids_brut is not None and self.tare is not None and self.tare >= self.poids_brut:
            erreurs["tare"] = "La tare doit être inférieure au poids brut."
        if self.refaction is not None and not (0 <= self.refaction < 100):
            erreurs["refaction"] = "La réfaction doit être comprise entre 0 et 100 %."
        if self.parcelle_id and self.producteur_id and self.parcelle.producteur_id != self.producteur_id:
            erreurs["parcelle"] = "Cette parcelle n'appartient pas au producteur sélectionné."
        if self.lot_id and self.magasin_id and self.lot.magasin_id != self.magasin_id:
            erreurs["lot"] = "Le lot doit appartenir au même magasin que l'achat."
        if erreurs:
            raise ValidationError(erreurs)

    def save(self, *args, **kwargs):
        if self.prix_kg is None:
            self.prix_kg = self.campagne.prix_kg
        self.poids_net = self.calculer_poids_net(self.poids_brut, self.tare, self.refaction)
        self.montant = (self.poids_net * self.prix_kg).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)
        if not self.numero:
            self.numero = f"ACH-{self.date:%Y}-{self.pk:06d}"
            super().save(update_fields=["numero"])
