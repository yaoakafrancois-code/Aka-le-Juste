from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class Cooperative(models.Model):
    """Informations de la coopérative (une seule fiche par installation)."""

    nom = models.CharField(max_length=200, default="Ma coopérative")
    sigle = models.CharField(max_length=30, blank=True)
    numero_agrement = models.CharField("n° d'agrément", max_length=60, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    telephone = models.CharField("téléphone", max_length=40, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        verbose_name = "coopérative"
        verbose_name_plural = "coopérative"

    def __str__(self):
        return self.sigle or self.nom

    @classmethod
    def courante(cls):
        return cls.objects.first() or cls(nom="Ma coopérative")


class CampagneQuerySet(models.QuerySet):
    def active(self):
        return self.filter(active=True).order_by("-date_debut").first()


class Campagne(models.Model):
    """Campagne de commercialisation (principale ou intermédiaire) avec son prix bord champ."""

    libelle = models.CharField("libellé", max_length=60, unique=True, help_text="Ex. : 2026-2027 principale")
    date_debut = models.DateField("date de début")
    date_fin = models.DateField("date de fin")
    prix_kg = models.DecimalField(
        "prix bord champ (FCFA/kg)", max_digits=10, decimal_places=2, default=Decimal("0")
    )
    active = models.BooleanField(
        default=False, help_text="Campagne utilisée par défaut pour les nouveaux achats."
    )

    objects = CampagneQuerySet.as_manager()

    class Meta:
        ordering = ["-date_debut"]

    def __str__(self):
        return self.libelle

    def clean(self):
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({"date_fin": "La date de fin doit suivre la date de début."})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.active:
            Campagne.objects.exclude(pk=self.pk).filter(active=True).update(active=False)


class Section(models.Model):
    """Section (groupement de producteurs par zone)."""

    nom = models.CharField(max_length=100, unique=True)
    localite = models.CharField("localité", max_length=100, blank=True)
    delegue = models.CharField("délégué", max_length=100, blank=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Magasin(models.Model):
    """Magasin ou point de collecte."""

    code = models.CharField(max_length=20, unique=True)
    nom = models.CharField(max_length=100)
    localite = models.CharField("localité", max_length=100, blank=True)
    responsable = models.CharField(max_length=100, blank=True)
    capacite_kg = models.PositiveIntegerField("capacité (kg)", null=True, blank=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return f"{self.code} – {self.nom}"
