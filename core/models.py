import secrets
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

# Produits gérés : le logiciel adapte ses écrans (certification, humidité, qualité) au produit choisi.
PRODUITS = {
    "cacao": {"nom": "cacao", "titre": "Cacao", "livre": "Fèves de cacao", "prix": "2800"},
    "cafe": {"nom": "café", "titre": "Café", "livre": "Café (cerises ou café vert)", "prix": "1500"},
    "hevea": {"nom": "hévéa", "titre": "Hévéa", "livre": "Caoutchouc naturel (fond de tasse)", "prix": "300"},
    "palmier": {"nom": "palmier à huile", "titre": "Régimes de palme", "livre": "Régimes de palme", "prix": "60"},
}
PRODUIT_CHOICES = [("cacao", "Cacao"), ("cafe", "Café"), ("hevea", "Hévéa (caoutchouc)"), ("palmier", "Palmier à huile (régimes)")]


def nouvelle_cle():
    return secrets.token_urlsafe(24)


class Cooperative(models.Model):
    """Informations de la coopérative (une seule fiche par installation)."""

    nom = models.CharField(max_length=200, default="Ma coopérative")
    produit = models.CharField(
        "produit acheté", max_length=10, choices=PRODUIT_CHOICES, default="cacao",
        help_text="Cacao, café, hévéa ou palmier à huile : les écrans s'adaptent au produit.",
    )
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
    url_relais = models.URLField(
        "adresse du serveur Akagri (vue du propriétaire)", blank=True,
        help_text="Adresse du serveur internet qui reçoit le résumé, ex. https://akagri.exemple.ci. "
                  "Laisser vide si le logiciel est déjà installé sur un serveur.",
    )
    cle_relais = models.CharField(
        "clé secrète du propriétaire", max_length=64, default=nouvelle_cle, editable=False,
        help_text="Clé du lien privé donné au propriétaire.",
    )

    class Meta:
        verbose_name = "coopérative"
        verbose_name_plural = "coopérative"

    def __str__(self):
        return self.sigle or self.nom

    @classmethod
    def courante(cls):
        return cls.objects.first() or cls(nom="Ma coopérative")

    @property
    def est_cacao(self):
        """Filière café-cacao : certification, humidité et grade s'appliquent."""
        return self.produit in ("cacao", "cafe")

    @property
    def infos_produit(self):
        return PRODUITS.get(self.produit, PRODUITS["cacao"])


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


class ResumeRecu(models.Model):
    """Abonné à la vue du propriétaire : ce serveur reçoit le résumé envoyé par son bureau (souvent sans internet).

    L'administrateur du serveur crée la fiche avec la clé de l'abonné ; sans fiche active, l'envoi est refusé.
    """

    nom = models.CharField("structure abonnée", max_length=200)
    cle = models.CharField("clé secrète", max_length=64, unique=True,
                           help_text="Clé affichée dans la page « Propriétaire » du logiciel de l'abonné.")
    actif = models.BooleanField(default=True, help_text="Décocher pour suspendre l'abonnement.")
    donnees = models.JSONField(default=dict, blank=True, editable=False)
    recu_le = models.DateTimeField("dernier envoi", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "abonné (vue du propriétaire)"
        verbose_name_plural = "abonnés (vue du propriétaire)"
        ordering = ["nom"]

    def __str__(self):
        return self.nom
