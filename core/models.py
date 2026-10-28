from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class Cooperative(models.Model):
    """Informations de la coopérative (une seule fiche par installation)."""

    nom = models.CharField(max_length=200, default="Ma coopérative")
    sigle = models.CharField(max_length=30, blank=True)
    numero_agrement = models.CharField("n° d'agrément", max_length=60, blank=True)
    code_ccc = models.CharField(
        "code coopérative (CCC)", max_length=60, blank=True,
        help_text="Identifiant de la coopérative auprès du Conseil du Café-Cacao.",
    )
    numero_rccm = models.CharField("n° RCCM", max_length=60, blank=True)
    region = models.CharField("région", max_length=100, blank=True)
    departement = models.CharField("département", max_length=100, blank=True)
    sous_prefecture = models.CharField("sous-préfecture", max_length=100, blank=True)
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


class PrixDuJour(models.Model):
    """Prix d'achat appliqué un jour donné, à la place du prix fixé de la campagne."""

    campagne = models.ForeignKey("Campagne", on_delete=models.CASCADE, related_name="prix_du_jour")
    date = models.DateField()
    magasin = models.ForeignKey(
        "Magasin", on_delete=models.CASCADE, null=True, blank=True, related_name="prix_du_jour",
        help_text="Laisser vide pour appliquer ce prix dans tous les magasins.",
    )
    prix_kg = models.DecimalField("prix (FCFA/kg)", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "prix du jour"
        verbose_name_plural = "prix du jour"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["campagne", "date", "magasin"], name="prix_du_jour_unique"),
        ]

    def __str__(self):
        return f"{self.date:%d/%m/%Y} : {self.prix_kg} FCFA/kg"

    def clean(self):
        doublon = PrixDuJour.objects.filter(campagne_id=self.campagne_id, date=self.date, magasin=self.magasin)
        if self.campagne_id and doublon.exclude(pk=self.pk).exists():
            raise ValidationError("Un prix existe déjà pour cette date et ce magasin.")


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

    def prix_applicable(self, jour, magasin=None):
        """Prix du jour (du magasin, sinon général) s'il existe, sinon prix fixé de la campagne."""
        prix = self.prix_du_jour.filter(date=jour)
        trouve = (magasin and prix.filter(magasin=magasin).first()) or prix.filter(magasin__isnull=True).first()
        return trouve.prix_kg if trouve else self.prix_kg


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
