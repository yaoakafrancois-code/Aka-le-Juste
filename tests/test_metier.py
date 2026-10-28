from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase, override_settings

from achats.models import Achat
from core.models import Campagne, Magasin, Section
from paiements.models import Avance, Paiement, Prime, situation_producteur
from core.models import PrixDuJour
from producteurs.models import CertificationProducteur, Parcelle, Producteur, Programme
from stocks.models import Exportateur, LigneLot, Livraison, Lot, stock_par_magasin


class Donnees(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagne = Campagne.objects.create(
            libelle="2026-2027", date_debut=date(2026, 10, 1), date_fin=date(2027, 3, 31),
            prix_kg=Decimal("2800"), active=True,
        )
        cls.section = Section.objects.create(nom="Gnamagui")
        cls.magasin = Magasin.objects.create(code="M01", nom="Central", capacite_kg=10000)
        cls.autre_magasin = Magasin.objects.create(code="M02", nom="Annexe")
        cls.producteur = Producteur.objects.create(nom="Kouassi", prenoms="Jean", section=cls.section)
        cls.parcelle = Parcelle.objects.create(producteur=cls.producteur, superficie_ha=Decimal("2.5"))

    def achat(self, **kw):
        valeurs = dict(campagne=self.campagne, producteur=self.producteur, magasin=self.magasin,
                       poids_brut=Decimal("103"), tare=Decimal("3"), date=date(2026, 10, 15))
        valeurs.update(kw)
        return Achat.objects.create(**valeurs)


@override_settings(ALLOWED_HOSTS=["testserver"])
class CalculsTests(Donnees):
    def test_codes_generes(self):
        self.assertEqual(self.producteur.code, f"P{self.producteur.pk:05d}")
        self.assertTrue(self.parcelle.code.startswith(self.producteur.code))
        a = self.achat()
        self.assertEqual(a.numero, f"ACH-2026-{a.pk:06d}")

    def test_poids_net_et_montant(self):
        a = self.achat(refaction=Decimal("2"))
        # (103 - 3) * (1 - 2 %) = 98 kg ; 98 * 2800 = 274 400
        self.assertEqual(a.poids_net, Decimal("98.00"))
        self.assertEqual(a.prix_kg, Decimal("2800"))
        self.assertEqual(a.montant, Decimal("274400"))

    def test_prix_specifique(self):
        a = self.achat(prix_kg=Decimal("2900"))
        self.assertEqual(a.montant, Decimal("290000"))

    def test_une_seule_campagne_active(self):
        nouvelle = Campagne.objects.create(libelle="2027-2028", date_debut=date(2027, 10, 1),
                                           date_fin=date(2028, 3, 31), active=True)
        self.campagne.refresh_from_db()
        self.assertFalse(self.campagne.active)
        self.assertEqual(Campagne.objects.active(), nouvelle)

    def test_situation_producteur(self):
        self.achat()  # 280 000
        Prime.objects.create(campagne=self.campagne, producteur=self.producteur, montant=Decimal("10000"))
        Avance.objects.create(campagne=self.campagne, producteur=self.producteur, montant=Decimal("50000"))
        Paiement.objects.create(campagne=self.campagne, producteur=self.producteur, montant=Decimal("200000"))
        s = situation_producteur(self.producteur)
        self.assertEqual(s["achats"], Decimal("280000"))
        self.assertEqual(s["solde"], Decimal("40000"))

    def test_stock_exclut_lots_livres(self):
        a1, a2 = self.achat(), self.achat()
        lot = Lot.objects.create(magasin=self.magasin, campagne=self.campagne)
        LigneLot.placer(lot, a1)
        Lot.objects.filter(pk=lot.pk).update(statut="livre")
        ligne = next(l for l in stock_par_magasin() if l["magasin"] == self.magasin)
        self.assertEqual(ligne["poids"], a2.poids_net)
        self.assertEqual(ligne["non_certifie"], a2.poids_net)
        self.assertEqual(ligne["taux_remplissage"], Decimal("1"))

    def test_prix_du_jour(self):
        PrixDuJour.objects.create(campagne=self.campagne, date=date(2026, 10, 15), prix_kg=Decimal("2900"))
        PrixDuJour.objects.create(campagne=self.campagne, date=date(2026, 10, 15), magasin=self.autre_magasin,
                                  prix_kg=Decimal("2950"))
        a = self.achat()
        self.assertEqual((a.prix_kg, a.source_prix), (Decimal("2900"), "jour"))
        self.assertEqual(self.achat(magasin=self.autre_magasin).prix_kg, Decimal("2950"))
        self.assertEqual(self.achat(date=date(2026, 10, 16)).source_prix, "campagne")
        self.assertEqual(self.achat(prix_kg=Decimal("3000")).source_prix, "manuel")


class CertificationTests(Donnees):
    """Exemple : producteur de 3 ha certifié RA, rendement de référence 500 kg/ha → 1 500 kg certifiables."""

    def setUp(self):
        self.ra = Programme.objects.create(code="RA", nom="Rainforest Alliance", prime_kg=Decimal("50"),
                                           rendement_reference_kg_ha=Decimal("500"))
        Parcelle.objects.filter(pk=self.parcelle.pk).update(superficie_ha=Decimal("3"))
        self.certif = CertificationProducteur.objects.create(
            producteur=self.producteur, programme=self.ra, campagne=self.campagne)

    def test_quota_depuis_superficie(self):
        self.assertEqual(self.certif.quota_kg, Decimal("1500.00"))

    def test_recu_500_kg_certifie(self):
        a = self.achat(poids_brut=Decimal("505"), tare=Decimal("5"))
        self.assertEqual((a.poids_certifie, a.poids_non_certifie), (Decimal("500.00"), Decimal("0.00")))
        self.assertEqual(a.programme, self.ra)
        self.assertEqual(a.montant, Decimal("1400000"))
        self.assertEqual(a.montant_prime, Decimal("25000"))
        self.assertEqual(situation_producteur(self.producteur)["solde"], Decimal("1425000"))

    def test_depassement_du_volume_estime(self):
        self.achat(poids_brut=Decimal("1203"))  # 1 200 kg certifiés
        a = self.achat(poids_brut=Decimal("503"))  # 300 restants
        self.assertEqual((a.poids_certifie, a.poids_non_certifie), (Decimal("300.00"), Decimal("200.00")))
        a3 = self.achat()
        self.assertEqual(a3.poids_certifie, 0)
        self.assertIsNone(a3.programme)

    def test_producteur_en_conversion_ou_force_non_certifie(self):
        self.assertEqual(self.achat(vendre_non_certifie=True).poids_certifie, 0)
        CertificationProducteur.objects.filter(pk=self.certif.pk).update(statut="conversion")
        self.assertEqual(self.achat().poids_certifie, 0)

    def test_segregation_des_lots(self):
        a = self.achat(poids_brut=Decimal("1703"))  # 1 500 certifiés + 200 non certifiés
        lot_ra = Lot.objects.create(magasin=self.magasin, campagne=self.campagne, programme=self.ra)
        lot_conv = Lot.objects.create(magasin=self.magasin, campagne=self.campagne)
        LigneLot.placer(lot_ra, a)
        LigneLot.placer(lot_conv, a)
        self.assertEqual(lot_ra.poids_net, Decimal("1500.00"))
        self.assertEqual(lot_conv.poids_net, Decimal("200.00"))
        self.assertIsNone(LigneLot.placer(lot_ra, a))  # plus rien à placer
        self.assertTrue(lot_ra.numero.startswith("LOT-M01-RA-"))
        with self.assertRaises(Exception):
            Livraison.verifier_lots([lot_ra, lot_conv])

    def test_grade_calcule(self):
        lot = Lot.objects.create(magasin=self.magasin, campagne=self.campagne, taux_moisi=Decimal("2"),
                                 taux_ardoise=Decimal("3"), taux_defauts=Decimal("1"), humidite=Decimal("7"))
        self.assertEqual(lot.grade, "grade1")
        lot.taux_ardoise = Decimal("7")
        lot.save()
        self.assertEqual(lot.grade, "grade2")
        lot.humidite = Decimal("9")
        lot.save()
        self.assertEqual(lot.grade, "hors_standard")


@override_settings(ALLOWED_HOSTS=["testserver"])
class VuesTests(Donnees):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@example.com", "motdepasse123")
        self.client.force_login(self.user)

    def test_connexion_obligatoire(self):
        self.client.logout()
        r = self.client.get("/achats/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/connexion/", r["Location"])

    def test_saisie_achat(self):
        r = self.client.post("/achats/nouveau/", {
            "date": "2026-10-20", "campagne": self.campagne.pk, "magasin": self.magasin.pk,
            "producteur": self.producteur.pk, "parcelle": self.parcelle.pk, "nombre_sacs": 2,
            "poids_brut": "130", "tare": "2", "refaction": "0", "qualite": "grade1", "prix_kg": "",
        })
        achat = Achat.objects.get()
        self.assertRedirects(r, f"/achats/{achat.pk}/")
        self.assertEqual(achat.montant, Decimal("358400"))
        self.assertEqual(achat.agent, self.user)

    def test_achat_tare_invalide(self):
        r = self.client.post("/achats/nouveau/", {
            "date": "2026-10-20", "campagne": self.campagne.pk, "magasin": self.magasin.pk,
            "producteur": self.producteur.pk, "nombre_sacs": 1, "poids_brut": "10", "tare": "12",
            "refaction": "0", "qualite": "grade1",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Achat.objects.exists())

    def test_parcelle_d_un_autre_producteur_refusee(self):
        autre = Producteur.objects.create(nom="Yao", prenoms="Aya")
        parcelle_autre = Parcelle.objects.create(producteur=autre, superficie_ha=1)
        r = self.client.post("/achats/nouveau/", {
            "date": "2026-10-20", "campagne": self.campagne.pk, "magasin": self.magasin.pk,
            "producteur": self.producteur.pk, "parcelle": parcelle_autre.pk, "nombre_sacs": 1,
            "poids_brut": "60", "tare": "1", "refaction": "0", "qualite": "grade1",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Achat.objects.exists())

    def test_paiement_limite_au_solde(self):
        self.achat()  # 280 000 dus
        donnees = {"date": "2026-10-21", "campagne": self.campagne.pk, "producteur": self.producteur.pk,
                   "mode": "especes"}
        r = self.client.post("/paiements/nouveau/", {**donnees, "montant": "300000"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Paiement.objects.exists())
        r = self.client.post("/paiements/nouveau/", {**donnees, "montant": "280000"})
        paiement = Paiement.objects.get()
        self.assertRedirects(r, f"/paiements/{paiement.pk}/recu/")

    def test_cycle_lot_livraison(self):
        a1 = self.achat()
        a_autre_magasin = self.achat(magasin=self.autre_magasin)
        lot = Lot.objects.create(magasin=self.magasin, campagne=self.campagne)
        self.client.post(f"/stocks/lots/{lot.pk}/achats/", {"achats": [a1.pk, a_autre_magasin.pk]})
        self.assertEqual([l.achat for l in lot.lignes.all()], [a1])  # l'achat d'un autre magasin est ignoré
        self.client.post(f"/stocks/lots/{lot.pk}/statut/", {"statut": "ferme"})
        lot.refresh_from_db()
        self.assertEqual(lot.statut, "ferme")

        exportateur = Exportateur.objects.create(nom="Export SA")
        self.client.post("/stocks/livraisons/nouvelle/", {
            "date": "2026-11-01", "exportateur": exportateur.pk, "lots": [lot.pk],
            "poids_livre": "99.5", "prix_kg": "2950", "destination": "abidjan", "numero_connaissement": "CN-1",
        })
        livraison = Livraison.objects.get()
        lot.refresh_from_db()
        self.assertEqual(lot.statut, "livre")
        self.assertEqual(livraison.ecart_poids, Decimal("-0.50"))
        self.assertEqual(livraison.nombre_sacs, 1)
        r = self.client.get(f"/stocks/livraisons/{livraison.pk}/connaissement/")
        self.assertContains(r, "CN-1")
        self.assertContains(r, self.producteur.code)

        # Un achat placé dans un lot ne peut plus être modifié.
        r = self.client.post(f"/achats/{a1.pk}/modifier/", {
            "date": "2026-10-15", "campagne": self.campagne.pk, "magasin": self.magasin.pk,
            "producteur": self.producteur.pk, "nombre_sacs": 1, "poids_brut": "200", "tare": "3",
            "refaction": "0", "qualite": "grade1",
        })
        self.assertEqual(r.status_code, 200)
        a1.refresh_from_db()
        self.assertEqual(a1.poids_brut, Decimal("103"))

        # Supprimer la livraison remet le lot en stock.
        self.client.post(f"/stocks/livraisons/{livraison.pk}/supprimer/")
        lot.refresh_from_db()
        self.assertEqual(lot.statut, "ferme")

    def test_pages_principales(self):
        a = self.achat()
        for url in ["/", "/rapports/", "/producteurs/", f"/producteurs/{self.producteur.pk}/",
                    "/producteurs/parcelles/", "/achats/", f"/achats/{a.pk}/recu/", "/paiements/situation/",
                    f"/paiements/releve/{self.producteur.pk}/", "/stocks/", "/stocks/lots/", "/stocks/livraisons/",
                    "/achats/export.csv", "/producteurs/parcelles/export.csv", "/producteurs/certifications/",
                    "/producteurs/certifications/export.csv", "/stocks/livraisons/export-ccc.csv",
                    f"/producteurs/{self.producteur.pk}/infos.json", "/manifest.webmanifest", "/sw.js"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


@override_settings(ALLOWED_HOSTS=["testserver"])
class RolesTests(Donnees):
    def test_agent_ne_peut_pas_payer(self):
        call_command("init_coop", stdout=open("/dev/null", "w"))
        agent = User.objects.create_user("agent", password="motdepasse123")
        agent.groups.add(Group.objects.get(name="Agent d'achat"))
        self.client.force_login(agent)
        self.assertEqual(self.client.get("/achats/nouveau/").status_code, 200)
        self.assertEqual(self.client.get("/paiements/nouveau/").status_code, 403)

    def test_donnees_demo(self):
        Producteur.objects.all().delete()
        call_command("init_coop", "--demo", stdout=open("/dev/null", "w"))
        self.assertEqual(Producteur.objects.count(), 20)
        self.assertTrue(Livraison.objects.exists())
