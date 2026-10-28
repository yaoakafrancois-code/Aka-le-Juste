from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.urls import reverse

from core.models import Campagne, Section


class Producteur(models.Model):
    SEXE_CHOICES = [("H", "Homme"), ("F", "Femme")]

    code = models.CharField(max_length=20, unique=True, blank=True, help_text="Généré automatiquement si vide.")
    nom = models.CharField(max_length=100)
    prenoms = models.CharField("prénoms", max_length=150)
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES, blank=True)
    date_naissance = models.DateField("date de naissance", null=True, blank=True)
    telephone = models.CharField("téléphone", max_length=40, blank=True)
    numero_piece = models.CharField("n° pièce d'identité", max_length=60, blank=True)
    numero_carte_ccc = models.CharField(
        "n° carte producteur", max_length=60, blank=True,
        help_text="Numéro de la carte du producteur délivrée par l'organe de régulation.",
    )
    section = models.ForeignKey(Section, on_delete=models.PROTECT, null=True, blank=True, related_name="producteurs")
    village = models.CharField(max_length=100, blank=True)
    date_adhesion = models.DateField("date d'adhésion", null=True, blank=True)
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nom", "prenoms"]

    def __str__(self):
        return f"{self.code} – {self.nom_complet}"

    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenoms}"

    def get_absolute_url(self):
        return reverse("producteurs:detail", args=[self.pk])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"P{self.pk:05d}"
            super().save(update_fields=["code"])

    @property
    def superficie_totale(self):
        return self.parcelles.aggregate(s=models.Sum("superficie_ha"))["s"] or 0


class Parcelle(models.Model):
    EUDR_CHOICES = [
        ("a_verifier", "À vérifier"),
        ("conforme", "Conforme (sans déforestation)"),
        ("non_conforme", "Non conforme"),
    ]

    producteur = models.ForeignKey(Producteur, on_delete=models.CASCADE, related_name="parcelles")
    code = models.CharField(max_length=30, unique=True, blank=True, help_text="Généré automatiquement si vide.")
    localite = models.CharField("localité", max_length=100, blank=True)
    superficie_ha = models.DecimalField("superficie (ha)", max_digits=8, decimal_places=2)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    polygone_geojson = models.TextField(
        "polygone (GeoJSON)", blank=True,
        help_text="Contour de la parcelle au format GeoJSON (obligatoire au-delà de 4 ha pour l'EUDR).",
    )
    annee_creation = models.PositiveIntegerField("année de création", null=True, blank=True)
    nombre_plants = models.PositiveIntegerField("nombre de plants", null=True, blank=True)
    certifiee = models.BooleanField(
        "parcelle incluse dans la certification", default=True,
        help_text="Décocher si la parcelle est exclue du périmètre certifié (ex. zone protégée, non auditée).",
    )
    statut_eudr = models.CharField("statut EUDR", max_length=20, choices=EUDR_CHOICES, default="a_verifier")

    class Meta:
        ordering = ["producteur__nom", "code"]

    def __str__(self):
        return f"{self.code} ({self.superficie_ha} ha)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"{self.producteur.code}-PA{self.pk:04d}"
            super().save(update_fields=["code"])

    @property
    def geolocalisee(self):
        return self.latitude is not None and self.longitude is not None


class Programme(models.Model):
    """Programme de certification ou de durabilité (Rainforest Alliance, ARS 1000, Fairtrade…)."""

    code = models.CharField(max_length=20, unique=True, help_text="Ex. : RA, ARS1000, FT")
    nom = models.CharField(max_length=100)
    rendement_reference_kg_ha = models.DecimalField(
        "rendement de référence (kg/ha)", max_digits=8, decimal_places=2, default=Decimal("500"),
        help_text="Sert à estimer la production certifiable quand aucune estimation n'est saisie.",
    )
    prime_kg = models.DecimalField(
        "prime producteur (FCFA/kg)", max_digits=8, decimal_places=2, default=Decimal("0"),
        help_text="Prime de certification due au producteur par kg certifié (calculée sur chaque reçu).",
    )
    numero_certificat = models.CharField(
        "n° de certificat de la coopérative", max_length=80, blank=True,
        help_text="Certificat du groupe (détenteur de certificat RA, attestation ARS 1000…).",
    )
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "programme de certification"
        verbose_name_plural = "programmes de certification"

    def __str__(self):
        return self.nom


class CertificationProducteur(models.Model):
    """Statut d'un producteur dans un programme pour une campagne (issu des audits / inspections internes)."""

    STATUT_CHOICES = [
        ("certifie", "Certifié"),
        ("conversion", "En conversion / candidat"),
        ("suspendu", "Suspendu"),
        ("exclu", "Exclu"),
    ]
    NIVEAU_CHOICES = [("", "–"), ("bronze", "Bronze"), ("argent", "Argent"), ("or", "Or")]

    producteur = models.ForeignKey(Producteur, on_delete=models.CASCADE, related_name="certifications")
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="certifications")
    campagne = models.ForeignKey(Campagne, on_delete=models.PROTECT, related_name="certifications")
    statut = models.CharField(max_length=12, choices=STATUT_CHOICES, default="certifie")
    niveau = models.CharField(
        max_length=10, choices=NIVEAU_CHOICES, blank=True, help_text="Niveau ARS 1000 (bronze, argent, or)."
    )
    numero_membre = models.CharField(
        "n° membre / code certification", max_length=60, blank=True,
        help_text="Identifiant du producteur dans la liste des membres certifiés.",
    )
    superficie_certifiee_ha = models.DecimalField(
        "superficie certifiée (ha)", max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Par défaut : somme des parcelles incluses dans la certification.",
    )
    production_estimee_kg = models.DecimalField(
        "production estimée (kg)", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Volume certifiable maximum pour la campagne. Par défaut : superficie × rendement de référence.",
    )
    date_inspection_interne = models.DateField("date d'inspection interne", null=True, blank=True)
    date_audit = models.DateField("date d'audit externe", null=True, blank=True)
    observations = models.TextField(blank=True)

    class Meta:
        ordering = ["-campagne__date_debut", "programme__code"]
        verbose_name = "certification producteur"
        verbose_name_plural = "certifications producteurs"
        constraints = [
            models.UniqueConstraint(fields=["producteur", "programme", "campagne"], name="certification_unique"),
        ]

    def __str__(self):
        return f"{self.programme.code} {self.campagne} – {self.get_statut_display()}"

    def clean(self):
        if self.production_estimee_kg is not None and self.production_estimee_kg < 0:
            raise ValidationError({"production_estimee_kg": "La production estimée doit être positive."})

    @property
    def superficie(self):
        if self.superficie_certifiee_ha is not None:
            return self.superficie_certifiee_ha
        return self.producteur.parcelles.filter(certifiee=True).aggregate(s=Sum("superficie_ha"))["s"] or Decimal("0")

    @property
    def quota_kg(self):
        """Volume certifiable de la campagne (estimation de production)."""
        if self.production_estimee_kg is not None:
            return self.production_estimee_kg
        return (self.superficie * self.programme.rendement_reference_kg_ha).quantize(Decimal("0.01"))

    def volume_achete(self, exclure_achat=None):
        achats = self.producteur.achats.filter(campagne=self.campagne, programme=self.programme)
        if exclure_achat is not None and exclure_achat.pk:
            achats = achats.exclude(pk=exclure_achat.pk)
        return achats.aggregate(p=Sum("poids_certifie"))["p"] or Decimal("0")

    def volume_restant(self, exclure_achat=None):
        return max(self.quota_kg - self.volume_achete(exclure_achat), Decimal("0"))


def certification_valide(producteur, campagne, programme=None):
    """Certification « certifié » du producteur pour la campagne (programme demandé, sinon la première)."""
    qs = producteur.certifications.filter(campagne=campagne, statut="certifie", programme__actif=True)
    if programme is not None:
        qs = qs.filter(programme=programme)
    return qs.select_related("programme").order_by("programme__code").first()
