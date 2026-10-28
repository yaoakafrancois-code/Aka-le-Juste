from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from core.models import Campagne, Magasin
from producteurs.models import Programme

# Limites de qualité (% en nombre de fèves sur l'épreuve à la coupe) par grade,
# d'après la norme ISO 2451 reprise par la réglementation ivoirienne. À vérifier
# avec les seuils en vigueur communiqués par le Conseil du Café-Cacao.
NORMES_GRADE = {
    "grade1": {"moisi": Decimal("3"), "ardoise": Decimal("3"), "defauts": Decimal("3")},
    "grade2": {"moisi": Decimal("4"), "ardoise": Decimal("8"), "defauts": Decimal("6")},
}
HUMIDITE_MAX = Decimal("8")
GRAINAGE_MAX = 100  # fèves pour 100 g


class Exportateur(models.Model):
    """Acheteur des lots (exportateur, usinier, intermédiaire agréé)."""

    nom = models.CharField(max_length=150, unique=True)
    numero_agrement = models.CharField("n° d'agrément", max_length=60, blank=True)
    code_ccc = models.CharField("code exportateur (CCC)", max_length=60, blank=True)
    contact = models.CharField(max_length=100, blank=True)
    telephone = models.CharField("téléphone", max_length=40, blank=True)
    adresse = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Lot(models.Model):
    """Regroupement d'achats d'un magasin, livré en une fois (unité de traçabilité).

    Un lot est soit certifié pour un programme (RA, ARS 1000…), soit conventionnel :
    les deux ne sont jamais mélangés (ségrégation).
    """

    STATUT_CHOICES = [
        ("ouvert", "Ouvert"),
        ("ferme", "Fermé (prêt à livrer)"),
        ("livre", "Livré"),
    ]
    GRADE_CHOICES = [
        ("grade1", "Grade I"),
        ("grade2", "Grade II"),
        ("hors_standard", "Hors standard (sous-grade)"),
    ]

    numero = models.CharField("n° de lot", max_length=30, unique=True, blank=True)
    magasin = models.ForeignKey(Magasin, on_delete=models.PROTECT, related_name="lots")
    campagne = models.ForeignKey(Campagne, on_delete=models.PROTECT, related_name="lots")
    programme = models.ForeignKey(
        Programme, on_delete=models.PROTECT, null=True, blank=True, related_name="lots",
        verbose_name="programme de certification", help_text="Laisser vide pour un lot conventionnel (non certifié).",
    )
    date_creation = models.DateField("date de création", default=timezone.localdate)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default="ouvert")
    # Analyse qualité (épreuve à la coupe) avant expédition.
    date_analyse = models.DateField("date de l'analyse", null=True, blank=True)
    humidite = models.DecimalField("humidité (%)", max_digits=5, decimal_places=2, null=True, blank=True)
    grainage = models.PositiveIntegerField("grainage (fèves / 100 g)", null=True, blank=True)
    taux_moisi = models.DecimalField("fèves moisies (%)", max_digits=5, decimal_places=2, null=True, blank=True)
    taux_ardoise = models.DecimalField("fèves ardoisées (%)", max_digits=5, decimal_places=2, null=True, blank=True)
    taux_defauts = models.DecimalField(
        "fèves mitées, germées ou plates (%)", max_digits=5, decimal_places=2, null=True, blank=True
    )
    grade = models.CharField(max_length=15, choices=GRADE_CHOICES, blank=True,
                             help_text="Calculé automatiquement quand l'analyse est complète.")
    observations = models.TextField(blank=True)

    class Meta:
        ordering = ["-date_creation", "-id"]

    def __str__(self):
        return self.numero

    def get_absolute_url(self):
        return reverse("stocks:lot_detail", args=[self.pk])

    def save(self, *args, **kwargs):
        calcule = self.grade_calcule()
        if calcule:
            self.grade = calcule
        super().save(*args, **kwargs)
        if not self.numero:
            prefixe = self.programme.code.upper() if self.programme_id else "CONV"
            self.numero = f"LOT-{self.magasin.code}-{prefixe}-{self.pk:05d}"
            super().save(update_fields=["numero"])

    @property
    def certifie(self):
        return self.programme_id is not None

    @property
    def type_produit(self):
        return f"Certifié {self.programme.code}" if self.programme_id else "Conventionnel (non certifié)"

    def grade_calcule(self):
        """Grade selon l'analyse ; None si l'analyse est incomplète."""
        valeurs = {"moisi": self.taux_moisi, "ardoise": self.taux_ardoise, "defauts": self.taux_defauts}
        if any(v is None for v in valeurs.values()):
            return None
        if self.humidite is not None and self.humidite > HUMIDITE_MAX:
            return "hors_standard"
        for grade, limites in NORMES_GRADE.items():
            if all(valeurs[k] <= limites[k] for k in limites):
                return grade
        return "hors_standard"

    @property
    def alertes_qualite(self):
        alertes = []
        if self.humidite is not None and self.humidite > HUMIDITE_MAX:
            alertes.append(f"Humidité supérieure à {HUMIDITE_MAX} %")
        if self.grainage is not None and self.grainage > GRAINAGE_MAX:
            alertes.append(f"Grainage supérieur à {GRAINAGE_MAX} fèves / 100 g")
        return alertes

    @property
    def poids_net(self):
        return self.lignes.aggregate(p=Sum("poids"))["p"] or Decimal("0")

    @property
    def nombre_sacs(self):
        return self.lignes.aggregate(n=Sum("sacs"))["n"] or 0

    @property
    def valeur_achat(self):
        return sum((l.valeur for l in self.lignes.select_related("achat")), Decimal("0"))


class LigneLot(models.Model):
    """Part d'un achat placée dans un lot (la part certifiée et la part conventionnelle vont dans des lots distincts)."""

    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="lignes")
    achat = models.ForeignKey("achats.Achat", on_delete=models.PROTECT, related_name="lignes_lot")
    certifie = models.BooleanField()
    poids = models.DecimalField("poids (kg)", max_digits=10, decimal_places=2)
    sacs = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["achat__date", "achat__id"]
        constraints = [models.UniqueConstraint(fields=["lot", "achat"], name="ligne_lot_unique")]

    def __str__(self):
        return f"{self.achat.numero} → {self.lot.numero} ({self.poids} kg)"

    @property
    def valeur(self):
        return (self.poids * self.achat.prix_kg).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    @classmethod
    def placer(cls, lot, achat):
        """Place dans le lot la part disponible de l'achat qui correspond au type du lot. Renvoie la ligne ou None."""
        if achat.magasin_id != lot.magasin_id or achat.campagne_id != lot.campagne_id:
            return None
        if lot.certifie and achat.programme_id != lot.programme_id:
            return None
        disponible = achat.poids_disponible(lot.certifie)
        if disponible <= 0:
            return None
        sacs = round(achat.nombre_sacs * disponible / achat.poids_net) if achat.poids_net else 0
        ligne, cree = cls.objects.get_or_create(
            lot=lot, achat=achat, defaults={"certifie": lot.certifie, "poids": disponible, "sacs": sacs}
        )
        if not cree:
            ligne.poids += disponible
            ligne.sacs += sacs
            ligne.save(update_fields=["poids", "sacs"])
        return ligne


class Livraison(models.Model):
    """Expédition d'un ou plusieurs lots à un exportateur, avec les informations du connaissement."""

    DESTINATION_CHOICES = [
        ("abidjan", "Port d'Abidjan"),
        ("san_pedro", "Port de San Pedro"),
        ("usine", "Usine de transformation"),
        ("autre", "Autre"),
    ]

    numero = models.CharField("n° de livraison", max_length=30, unique=True, blank=True)
    numero_connaissement = models.CharField(
        "n° de connaissement", max_length=60, blank=True,
        help_text="Numéro du connaissement délivré par le Conseil du Café-Cacao.",
    )
    date = models.DateField("date d'expédition", default=timezone.localdate)
    exportateur = models.ForeignKey(Exportateur, on_delete=models.PROTECT, related_name="livraisons")
    lots = models.ManyToManyField(Lot, related_name="livraisons")
    destination = models.CharField(max_length=15, choices=DESTINATION_CHOICES, default="abidjan")
    adresse_destination = models.CharField("magasin / adresse de destination", max_length=200, blank=True)
    nombre_sacs = models.PositiveIntegerField("nombre de sacs expédiés", null=True, blank=True,
                                              help_text="Par défaut : sacs des lots.")
    poids_brut = models.DecimalField("poids brut expédié (kg)", max_digits=12, decimal_places=2, null=True,
                                     blank=True)
    poids_livre = models.DecimalField("poids net expédié (kg)", max_digits=12, decimal_places=2)
    poids_reconnu = models.DecimalField(
        "poids net reconnu à l'arrivée (kg)", max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Poids constaté par l'exportateur (pont-bascule) ; à compléter au retour du camion.",
    )
    numero_ticket_pesee = models.CharField("n° ticket de pesée (arrivée)", max_length=60, blank=True)
    prix_kg = models.DecimalField("prix de vente (FCFA/kg)", max_digits=10, decimal_places=2)
    transporteur = models.CharField(max_length=150, blank=True)
    immatriculation = models.CharField("immatriculation du camion", max_length=30, blank=True)
    immatriculation_remorque = models.CharField("immatriculation de la remorque", max_length=30, blank=True)
    chauffeur = models.CharField(max_length=150, blank=True)
    permis_chauffeur = models.CharField("n° permis du chauffeur", max_length=60, blank=True)
    telephone_chauffeur = models.CharField("téléphone du chauffeur", max_length=40, blank=True)
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

    @staticmethod
    def verifier_lots(lots):
        """Un connaissement ne mélange pas certifié et conventionnel, ni deux programmes, ni deux campagnes."""
        programmes = {lot.programme_id for lot in lots}
        if len(programmes) > 1:
            raise ValidationError("Les lots d'une même livraison doivent être du même type "
                                  "(tous conventionnels ou tous certifiés du même programme).")
        if len({lot.campagne_id for lot in lots}) > 1:
            raise ValidationError("Les lots d'une même livraison doivent appartenir à la même campagne.")

    @property
    def poids_final(self):
        return self.poids_reconnu if self.poids_reconnu is not None else self.poids_livre

    @property
    def montant(self):
        return self.poids_final * self.prix_kg

    @property
    def poids_lots(self):
        return sum((lot.poids_net for lot in self.lots.all()), Decimal("0"))

    @property
    def sacs_lots(self):
        return sum(lot.nombre_sacs for lot in self.lots.all())

    @property
    def ecart_poids(self):
        """Perte (négatif) ou gain de poids entre le stock et le poids reconnu ou expédié."""
        return self.poids_final - self.poids_lots

    @property
    def premier_lot(self):
        return self.lots.select_related("programme", "campagne", "magasin").first()

    @property
    def type_produit(self):
        lot = self.premier_lot
        return lot.type_produit if lot else ""

    @property
    def grade(self):
        """Grade le plus faible des lots expédiés."""
        ordre = [g for g, _ in Lot.GRADE_CHOICES]
        grades = [lot.grade for lot in self.lots.all() if lot.grade]
        if not grades:
            return ""
        return dict(Lot.GRADE_CHOICES)[max(grades, key=ordre.index)]


def stock_par_magasin(campagne=None):
    """Stock physique (kg) par magasin, en séparant certifié et non certifié.

    Stock = achats − parts placées dans des lots déjà livrés.
    """
    from achats.models import Achat

    lignes = []
    for magasin in Magasin.objects.all():
        achats = Achat.objects.filter(magasin=magasin)
        livrees = LigneLot.objects.filter(achat__magasin=magasin, lot__statut="livre")
        placees = LigneLot.objects.filter(achat__magasin=magasin)
        if campagne is not None:
            achats = achats.filter(campagne=campagne)
            livrees = livrees.filter(achat__campagne=campagne)
            placees = placees.filter(achat__campagne=campagne)

        def somme(qs, champ):
            return qs.aggregate(t=Sum(champ))["t"] or Decimal("0")

        certifie = somme(achats, "poids_certifie") - somme(livrees.filter(certifie=True), "poids")
        non_certifie = somme(achats, "poids_non_certifie") - somme(livrees.filter(certifie=False), "poids")
        poids = certifie + non_certifie
        lignes.append({
            "magasin": magasin,
            "poids": poids,
            "certifie": certifie,
            "non_certifie": non_certifie,
            "sacs": somme(achats, "nombre_sacs") - somme(livrees, "sacs"),
            "hors_lot": somme(achats, "poids_net") - somme(placees, "poids"),
            "taux_remplissage": (poids / magasin.capacite_kg * 100) if magasin.capacite_kg else None,
        })
    return lignes
