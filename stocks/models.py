from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from core.models import Campagne, Magasin


class Exportateur(models.Model):
    """Acheteur des lots (exportateur, usinier, intermédiaire agréé)."""

    nom = models.CharField(max_length=150, unique=True)
    numero_agrement = models.CharField("n° d'agrément", max_length=60, blank=True)
    contact = models.CharField(max_length=100, blank=True)
    telephone = models.CharField("téléphone", max_length=40, blank=True)
    adresse = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Lot(models.Model):
    """Regroupement d'achats d'un magasin, livré en une fois (unité de traçabilité)."""

    STATUT_CHOICES = [
        ("ouvert", "Ouvert"),
        ("ferme", "Fermé (prêt à livrer)"),
        ("livre", "Livré"),
    ]

    numero = models.CharField("n° de lot", max_length=30, unique=True, blank=True)
    magasin = models.ForeignKey(Magasin, on_delete=models.PROTECT, related_name="lots")
    campagne = models.ForeignKey(Campagne, on_delete=models.PROTECT, related_name="lots")
    date_creation = models.DateField("date de création", default=timezone.localdate)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default="ouvert")
    observations = models.TextField(blank=True)

    class Meta:
        ordering = ["-date_creation", "-id"]

    def __str__(self):
        return self.numero

    def get_absolute_url(self):
        return reverse("stocks:lot_detail", args=[self.pk])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.numero:
            self.numero = f"LOT-{self.magasin.code}-{self.pk:05d}"
            super().save(update_fields=["numero"])

    @property
    def poids_net(self):
        return self.achats.aggregate(p=Sum("poids_net"))["p"] or Decimal("0")

    @property
    def nombre_sacs(self):
        return self.achats.aggregate(n=Sum("nombre_sacs"))["n"] or 0

    @property
    def valeur_achat(self):
        return self.achats.aggregate(m=Sum("montant"))["m"] or Decimal("0")


class Livraison(models.Model):
    """Livraison d'un ou plusieurs lots à un exportateur."""

    numero = models.CharField("n° de livraison", max_length=30, unique=True, blank=True)
    date = models.DateField(default=timezone.localdate)
    exportateur = models.ForeignKey(Exportateur, on_delete=models.PROTECT, related_name="livraisons")
    lots = models.ManyToManyField(Lot, related_name="livraisons")
    poids_livre = models.DecimalField("poids livré / reconnu (kg)", max_digits=12, decimal_places=2)
    prix_kg = models.DecimalField("prix de vente (FCFA/kg)", max_digits=10, decimal_places=2)
    transporteur = models.CharField(max_length=150, blank=True)
    immatriculation = models.CharField("immatriculation du camion", max_length=30, blank=True)
    numero_bordereau = models.CharField("n° de bordereau / connaissement", max_length=60, blank=True)
    observations = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return self.numero

    def get_absolute_url(self):
        return reverse("stocks:livraison_detail", args=[self.pk])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.numero:
            self.numero = f"LIV-{self.date:%Y}-{self.pk:05d}"
            super().save(update_fields=["numero"])

    @property
    def montant(self):
        return self.poids_livre * self.prix_kg

    @property
    def poids_lots(self):
        return sum((lot.poids_net for lot in self.lots.all()), Decimal("0"))

    @property
    def ecart_poids(self):
        """Perte (négatif) ou gain de poids entre le stock et le poids reconnu à la livraison."""
        return self.poids_livre - self.poids_lots


def stock_par_magasin(campagne=None):
    """Stock physique (kg) par magasin : achats dont le lot n'est pas encore livré."""
    lignes = []
    for magasin in Magasin.objects.all():
        achats = magasin.achats.exclude(lot__statut="livre")
        if campagne is not None:
            achats = achats.filter(campagne=campagne)
        agg = achats.aggregate(p=Sum("poids_net"), s=Sum("nombre_sacs"), v=Sum("montant"))
        hors_lot = achats.filter(lot__isnull=True).aggregate(p=Sum("poids_net"))["p"] or Decimal("0")
        poids = agg["p"] or Decimal("0")
        lignes.append({
            "magasin": magasin,
            "poids": poids,
            "sacs": agg["s"] or 0,
            "valeur": agg["v"] or Decimal("0"),
            "hors_lot": hors_lot,
            "taux_remplissage": (poids / magasin.capacite_kg * 100) if magasin.capacite_kg else None,
        })
    return lignes
