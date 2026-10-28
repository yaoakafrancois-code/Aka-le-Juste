from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from core.models import Campagne
from producteurs.models import Producteur

MODE_CHOICES = [
    ("especes", "Espèces"),
    ("mobile_money", "Mobile Money"),
    ("cheque", "Chèque"),
    ("virement", "Virement bancaire"),
]


class Paiement(models.Model):
    """Règlement versé à un producteur pour ses livraisons."""

    numero = models.CharField("n° de paiement", max_length=30, unique=True, blank=True)
    date = models.DateField(default=timezone.localdate)
    campagne = models.ForeignKey(Campagne, on_delete=models.PROTECT, related_name="paiements")
    producteur = models.ForeignKey(Producteur, on_delete=models.PROTECT, related_name="paiements")
    montant = models.DecimalField("montant (FCFA)", max_digits=14, decimal_places=2)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="especes")
    reference = models.CharField("référence", max_length=100, blank=True,
                                 help_text="N° de transaction Mobile Money, de chèque…")
    observations = models.TextField(blank=True)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="+")
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.numero} – {self.producteur.nom_complet}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.numero:
            self.numero = f"PAI-{self.date:%Y}-{self.pk:06d}"
            super().save(update_fields=["numero"])


class Avance(models.Model):
    """Avance (pré-financement) accordée à un producteur, déduite de son solde."""

    date = models.DateField(default=timezone.localdate)
    campagne = models.ForeignKey(Campagne, on_delete=models.PROTECT, related_name="avances")
    producteur = models.ForeignKey(Producteur, on_delete=models.PROTECT, related_name="avances")
    montant = models.DecimalField("montant (FCFA)", max_digits=14, decimal_places=2)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="especes")
    motif = models.CharField(max_length=200, blank=True)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="+")

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"Avance {self.montant} – {self.producteur.nom_complet}"


class Prime(models.Model):
    """Prime versée en plus du prix (certification, qualité, fidélité…)."""

    TYPE_CHOICES = [
        ("certification", "Prime de certification"),
        ("qualite", "Prime de qualité"),
        ("fidelite", "Prime de fidélité"),
        ("ristourne", "Ristourne"),
        ("autre", "Autre"),
    ]

    date = models.DateField(default=timezone.localdate)
    campagne = models.ForeignKey(Campagne, on_delete=models.PROTECT, related_name="primes")
    producteur = models.ForeignKey(Producteur, on_delete=models.PROTECT, related_name="primes")
    type_prime = models.CharField("type", max_length=20, choices=TYPE_CHOICES, default="certification")
    montant = models.DecimalField("montant (FCFA)", max_digits=14, decimal_places=2)
    observations = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.get_type_prime_display()} {self.montant} – {self.producteur.nom_complet}"


def situation_producteur(producteur, campagne=None):
    """Situation financière d'un producteur.

    solde = achats + primes − paiements − avances
    Un solde positif est le montant que la coopérative doit encore au producteur ;
    un solde négatif est une dette du producteur (avance non couverte).
    """

    def total(qs, champ="montant"):
        if campagne is not None:
            qs = qs.filter(campagne=campagne)
        return qs.aggregate(t=Sum(champ))["t"] or 0

    achats = total(producteur.achats.all())
    primes = total(producteur.primes.all())
    paiements = total(producteur.paiements.all())
    avances = total(producteur.avances.all())
    return {
        "achats": achats,
        "poids": total(producteur.achats.all(), "poids_net"),
        "primes": primes,
        "paiements": paiements,
        "avances": avances,
        "solde": achats + primes - paiements - avances,
    }
