from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from core.models import Campagne, Magasin
from producteurs.models import Parcelle, Producteur, Programme, certification_valide

DEUX = Decimal("0.01")


def arrondi_franc(valeur):
    return Decimal(valeur).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class Achat(models.Model):
    """Achat (pesée) de fèves de cacao auprès d'un producteur.

    Le poids net est réparti automatiquement entre une part certifiée (dans la limite de la production
    estimée du producteur pour le programme) et une part non certifiée (conventionnelle).
    """

    QUALITE_CHOICES = [
        ("grade1", "Grade I"),
        ("grade2", "Grade II"),
        ("hors_standard", "Hors standard"),
    ]
    SOURCE_PRIX_CHOICES = [
        ("campagne", "Prix fixé de la campagne"),
        ("jour", "Prix du jour"),
        ("manuel", "Prix saisi"),
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
                                  help_text="Laisser vide : prix du jour s'il existe, sinon prix fixé de la campagne.")
    source_prix = models.CharField("origine du prix", max_length=10, choices=SOURCE_PRIX_CHOICES,
                                   default="campagne", editable=False)
    programme = models.ForeignKey(
        Programme, on_delete=models.PROTECT, null=True, blank=True, related_name="achats",
        verbose_name="programme de certification",
        help_text="Laisser vide : choix automatique selon la certification du producteur.",
    )
    vendre_non_certifie = models.BooleanField(
        "acheter comme non certifié", default=False,
        help_text="Cocher pour enregistrer tout le cacao en conventionnel, même si le producteur est certifié.",
    )
    poids_net = models.DecimalField("poids net (kg)", max_digits=10, decimal_places=2, editable=False)
    poids_certifie = models.DecimalField("poids certifié (kg)", max_digits=10, decimal_places=2,
                                         default=Decimal("0"), editable=False)
    poids_non_certifie = models.DecimalField("poids non certifié (kg)", max_digits=10, decimal_places=2,
                                             default=Decimal("0"), editable=False)
    montant = models.DecimalField("montant (FCFA)", max_digits=14, decimal_places=2, editable=False)
    prime_kg = models.DecimalField("prime (FCFA/kg certifié)", max_digits=8, decimal_places=2,
                                   default=Decimal("0"), editable=False)
    montant_prime = models.DecimalField("prime de certification (FCFA)", max_digits=14, decimal_places=2,
                                        default=Decimal("0"), editable=False)
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

    @property
    def est_certifie(self):
        return self.poids_certifie > 0

    @property
    def montant_certifie(self):
        return arrondi_franc(self.poids_certifie * self.prix_kg)

    @property
    def montant_non_certifie(self):
        return self.montant - self.montant_certifie

    @property
    def montant_total(self):
        return self.montant + self.montant_prime

    def certification(self):
        """Certification du producteur utilisée pour cet achat (ou None)."""
        if self.vendre_non_certifie:
            return None
        return certification_valide(self.producteur, self.campagne, self.programme)

    def clean(self):
        erreurs = {}
        if self.poids_brut is not None and self.tare is not None and self.tare >= self.poids_brut:
            erreurs["tare"] = "La tare doit être inférieure au poids brut."
        if self.refaction is not None and not (0 <= self.refaction < 100):
            erreurs["refaction"] = "La réfaction doit être comprise entre 0 et 100 %."
        if self.parcelle_id and self.producteur_id and self.parcelle.producteur_id != self.producteur_id:
            erreurs["parcelle"] = "Cette parcelle n'appartient pas au producteur sélectionné."
        if (self.programme_id and self.producteur_id and self.campagne_id and not self.vendre_non_certifie
                and certification_valide(self.producteur, self.campagne, self.programme) is None):
            erreurs["programme"] = "Ce producteur n'est pas certifié pour ce programme sur cette campagne."
        if erreurs:
            raise ValidationError(erreurs)

    def repartir(self):
        """Calcule poids net, part certifiée / non certifiée, prix, montant et prime."""
        self.poids_net = self.calculer_poids_net(self.poids_brut, self.tare, self.refaction)
        applicable = self.campagne.prix_applicable(self.date, self.magasin)
        if self.prix_kg is None:
            self.prix_kg = applicable
        if self.prix_kg != applicable:
            self.source_prix = "manuel"
        elif applicable != self.campagne.prix_kg:
            self.source_prix = "jour"
        else:
            self.source_prix = "campagne"

        certification = self.certification()
        certifie = Decimal("0")
        if certification is not None:
            certifie = min(self.poids_net, certification.volume_restant(exclure_achat=self))
        if certifie > 0:
            self.programme = certification.programme
            self.prime_kg = certification.programme.prime_kg
        else:
            self.programme = None
            self.prime_kg = Decimal("0")
        self.poids_certifie = certifie
        self.poids_non_certifie = self.poids_net - certifie
        self.montant = arrondi_franc(self.poids_net * self.prix_kg)
        self.montant_prime = arrondi_franc(self.poids_certifie * self.prime_kg)

    def save(self, *args, **kwargs):
        self.repartir()
        super().save(*args, **kwargs)
        if not self.numero:
            self.numero = f"ACH-{self.date:%Y}-{self.pk:06d}"
            super().save(update_fields=["numero"])

    # Répartition dans les lots -------------------------------------------------------------

    def poids_en_lot(self, certifie):
        return self.lignes_lot.filter(certifie=certifie).aggregate(p=Sum("poids"))["p"] or Decimal("0")

    def poids_disponible(self, certifie):
        """Poids pas encore placé dans un lot, pour la part certifiée ou non certifiée."""
        total = self.poids_certifie if certifie else self.poids_non_certifie
        return total - self.poids_en_lot(certifie)
