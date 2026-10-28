"""Initialise la coopérative : rôles (groupes) et, en option, des données de démonstration.

    python manage.py init_coop            # crée/met à jour les rôles
    python manage.py init_coop --demo     # + données d'exemple pour essayer le logiciel
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Campagne, Cooperative, Magasin, Section

# Rôle -> {application: actions autorisées sur tous ses modèles}
ROLES = {
    "Administrateur": {
        "core": "add change delete view", "producteurs": "add change delete view", "achats": "add change delete view",
        "paiements": "add change delete view", "stocks": "add change delete view", "auth": "add change delete view",
    },
    "Agent d'achat": {
        "core": "view", "producteurs": "add change view", "achats": "add change view", "paiements": "view",
        "stocks": "view",
    },
    "Comptable": {
        "core": "view", "producteurs": "view", "achats": "view", "paiements": "add change delete view",
        "stocks": "view",
    },
    "Magasinier": {
        "core": "view", "producteurs": "view", "achats": "view", "paiements": "view", "stocks": "add change view",
    },
}


class Command(BaseCommand):
    help = "Crée les rôles utilisateurs et, avec --demo, des données de démonstration."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Ajouter des données de démonstration.")

    @transaction.atomic
    def handle(self, *args, **options):
        for nom, droits in ROLES.items():
            groupe, _ = Group.objects.get_or_create(name=nom)
            perms = []
            for app, actions in droits.items():
                for action in actions.split():
                    perms += Permission.objects.filter(content_type__app_label=app, codename__startswith=f"{action}_")
            groupe.permissions.set(perms)
        if options["verbosity"]:
            self.stdout.write(self.style.SUCCESS(f"Rôles configurés : {', '.join(ROLES)}"))

        if not Cooperative.objects.exists():
            Cooperative.objects.create(nom="Ma coopérative")

        if options["demo"]:
            self.donnees_demo()

    def donnees_demo(self):
        from achats.models import Achat
        from paiements.models import Avance, Paiement, Prime
        from producteurs.models import Parcelle, Producteur
        from stocks.models import Exportateur, Livraison, Lot

        if Producteur.objects.exists():
            self.stdout.write(self.style.WARNING("Des producteurs existent déjà : données de démo ignorées."))
            return

        rnd = random.Random(42)
        Cooperative.objects.update(
            nom="Société Coopérative Agricole de Démonstration", sigle="SCOOP-DEMO",
            adresse="Soubré, Côte d'Ivoire", telephone="+225 07 00 00 00 00",
        )
        aujourd_hui = date.today()
        debut = date(aujourd_hui.year if aujourd_hui.month >= 10 else aujourd_hui.year - 1, 10, 1)
        campagne, _ = Campagne.objects.get_or_create(
            libelle=f"{debut.year}-{debut.year + 1} principale",
            defaults=dict(date_debut=debut, date_fin=date(debut.year + 1, 3, 31), prix_kg=Decimal("2800"), active=True),
        )
        sections = [Section.objects.get_or_create(nom=n, defaults={"localite": n})[0]
                    for n in ("Gnamagui", "Okrouyo", "Liliyo")]
        magasins = [
            Magasin.objects.get_or_create(code="M01", defaults=dict(
                nom="Magasin central", localite="Soubré", capacite_kg=200000))[0],
            Magasin.objects.get_or_create(code="M02", defaults=dict(
                nom="Point de collecte Okrouyo", localite="Okrouyo", capacite_kg=50000))[0],
        ]
        noms = ["Kouassi", "Koné", "Yao", "Traoré", "Konan", "Ouattara", "Kouamé", "Bamba", "N'Guessan", "Coulibaly"]
        prenoms = ["Jean", "Aya", "Mamadou", "Adjoua", "Koffi", "Fatou", "Serge", "Akissi", "Ibrahim", "Affoué"]
        producteurs = []
        for i in range(20):
            p = Producteur.objects.create(
                nom=rnd.choice(noms), prenoms=rnd.choice(prenoms), sexe=rnd.choice("HF"),
                telephone=f"07 {rnd.randint(10, 99)} {rnd.randint(10, 99)} {rnd.randint(10, 99)} {rnd.randint(10, 99)}",
                section=rnd.choice(sections), village=rnd.choice(["Gnamagui", "Okrouyo", "Liliyo", "Buyo"]),
                date_adhesion=date(rnd.randint(2010, 2024), 1, 1),
            )
            for _ in range(rnd.randint(1, 2)):
                Parcelle.objects.create(
                    producteur=p, localite=p.village, superficie_ha=Decimal(rnd.randint(10, 60)) / 10,
                    latitude=Decimal(f"5.{rnd.randint(700000, 999999)}"),
                    longitude=Decimal(f"-6.{rnd.randint(500000, 799999)}"),
                    certification=rnd.choice(["aucune", "rainforest", "fairtrade"]),
                    statut_eudr=rnd.choice(["conforme", "conforme", "a_verifier"]),
                )
            producteurs.append(p)

        fin = min(aujourd_hui, campagne.date_fin)
        jours = max((fin - debut).days, 1)
        for _ in range(80):
            p = rnd.choice(producteurs)
            sacs = rnd.randint(1, 8)
            Achat.objects.create(
                date=debut + timedelta(days=rnd.randint(0, jours)), campagne=campagne, producteur=p,
                parcelle=p.parcelles.first(), magasin=rnd.choice(magasins), nombre_sacs=sacs,
                poids_brut=Decimal(sacs * rnd.randint(60, 66)), tare=Decimal(sacs), humidite=Decimal("7.5"),
                refaction=Decimal(rnd.choice([0, 0, 0, 1, 2])),
            )
        for p in producteurs[:6]:
            Avance.objects.create(campagne=campagne, producteur=p, montant=Decimal("50000"), motif="Intrants",
                                  date=debut)
        for p in producteurs[:12]:
            du = sum(a.montant for a in p.achats.all())
            if du > 100000:
                Paiement.objects.create(campagne=campagne, producteur=p, montant=(du * Decimal("0.6")).quantize(1),
                                        mode=rnd.choice(["especes", "mobile_money"]), date=fin)
        for p in producteurs:
            if p.parcelles.filter(certification="rainforest").exists() and p.achats.exists():
                Prime.objects.create(campagne=campagne, producteur=p, type_prime="certification",
                                     montant=Decimal("15000"), date=fin)

        exportateur, _ = Exportateur.objects.get_or_create(nom="Exportateur Démo SA",
                                                           defaults={"numero_agrement": "EXP-0001"})
        lot = Lot.objects.create(magasin=magasins[0], campagne=campagne)
        ids = list(Achat.objects.filter(magasin=magasins[0]).order_by("date").values_list("pk", flat=True)[:15])
        Achat.objects.filter(pk__in=ids).update(lot=lot)
        lot.statut = "ferme"
        lot.save()
        livraison = Livraison.objects.create(
            exportateur=exportateur, poids_livre=(lot.poids_net * Decimal("0.995")).quantize(Decimal("0.01")),
            prix_kg=Decimal("2950"), transporteur="Transports Démo", immatriculation="1234 AB 01", date=fin,
        )
        livraison.lots.add(lot)
        Lot.objects.filter(pk=lot.pk).update(statut="livre")
        Lot.objects.create(magasin=magasins[1], campagne=campagne)
        self.stdout.write(self.style.SUCCESS("Données de démonstration créées."))
