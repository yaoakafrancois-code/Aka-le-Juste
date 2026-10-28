from django.db import models
from django.urls import reverse

from core.models import Section


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
    CERTIFICATION_CHOICES = [
        ("aucune", "Aucune"),
        ("rainforest", "Rainforest Alliance"),
        ("fairtrade", "Fairtrade"),
        ("bio", "Agriculture biologique"),
        ("autre", "Autre"),
    ]
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
    certification = models.CharField(max_length=20, choices=CERTIFICATION_CHOICES, default="aucune")
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
