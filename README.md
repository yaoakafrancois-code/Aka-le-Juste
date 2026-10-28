# CacaoCoop – Gestion des achats et de la collecte de cacao

Logiciel de gestion pour les coopératives cacaoyères : producteurs et parcelles, pesées et achats bord champ,
paiements et avances, stocks, lots et livraisons aux exportateurs, avec traçabilité jusqu'à la parcelle (EUDR).

Il fonctionne de deux façons, avec le même code :

- **Mode bureau** : sur un seul ordinateur de la coopérative, sans internet (base SQLite locale). Les autres postes
  du même réseau local peuvent s'y connecter avec leur navigateur.
- **Mode web** : sur un serveur, accessible depuis n'importe où (ordinateur, tablette, téléphone).

## Fonctionnalités

| Module | Ce qu'il fait |
|---|---|
| **Producteurs et parcelles** | Fiche producteur (identité, section, village, carte producteur), parcelles avec superficie, GPS, polygone GeoJSON, certification et statut EUDR. Export CSV de traçabilité. |
| **Achats et pesées** | Saisie de la pesée : sacs, poids brut, tare, humidité, réfaction, qualité. Calcul automatique du poids net et du montant au prix de la campagne. Reçu d'achat imprimable. Journal filtrable et export CSV. |
| **Paiements et avances** | Paiements (espèces, Mobile Money, chèque, virement), avances (pré-financement), primes (certification, qualité, ristourne). Situation de tous les producteurs (qui payer, qui doit encore une avance), relevé de compte imprimable. Un paiement ne peut pas dépasser le solde dû. |
| **Stocks, lots et livraisons** | Stock par magasin et taux de remplissage, constitution des lots, fermeture, livraison à un exportateur avec bordereau imprimable et calcul de l'écart de poids. Fiche de traçabilité par lot (producteurs et parcelles d'origine). |
| **Tableau de bord et rapports** | Tonnage acheté, montants, reste à payer, stock, achats par mois, par section, par magasin, par qualité, meilleurs producteurs. |
| **Utilisateurs et rôles** | Administrateur, Agent d'achat, Comptable, Magasinier, chacun avec ses droits. |

Calculs utilisés :

- Poids net = (poids brut − tare) × (1 − réfaction %)
- Montant = poids net × prix au kg (arrondi au franc)
- Solde producteur = achats + primes − paiements − avances (positif : la coopérative doit payer ; négatif : avance à récupérer)

## Mode bureau (un ordinateur, sans internet)

Prérequis : [Python 3.11 ou plus récent](https://www.python.org/downloads/) (sous Windows, cochez « Add Python to PATH »).
La première installation télécharge trois petits paquets ; ensuite, plus besoin d'internet.

- **Windows** : double-cliquez sur `lancer.bat`.
- **Linux / macOS** : `./lancer.sh`

Au premier lancement, le logiciel crée la base de données et vous demande un identifiant et un mot de passe
administrateur. Le navigateur s'ouvre ensuite sur <http://127.0.0.1:8000>.

Pour que d'autres postes du réseau local (Wi-Fi de la coopérative) accèdent au logiciel :
`lancer.bat --reseau` (ou `./lancer.sh --reseau`), puis ouvrez l'adresse affichée sur les autres postes.

Les données se trouvent dans le dossier `data/`. **Faites des sauvegardes régulières** :

```sh
.venv/bin/python manage.py sauvegarde                 # dans le dossier sauvegardes/
.venv/bin/python manage.py sauvegarde --dossier E:\   # sur une clé USB (Windows : .venv\Scripts\python)
```

Pour essayer le logiciel avec des données fictives (20 producteurs, 80 pesées, lots et livraison) :

```sh
.venv/bin/python manage.py init_coop --demo
```

## Premiers pas

1. Menu **Paramètres** : renseignez la coopérative, créez la **campagne** (dates et prix bord champ) et cochez « active »,
   puis les **sections**, les **magasins** et les **exportateurs**.
2. Créez les comptes utilisateurs dans **Paramètres → Utilisateurs** et attribuez-leur un groupe (rôle).
   Cochez « statut équipe » pour les administrateurs qui doivent accéder aux paramètres.
3. Enregistrez les **producteurs** et leurs **parcelles**.
4. Saisissez les **pesées** (menu Achats → Nouvelle pesée), imprimez le reçu.
5. Payez les producteurs depuis **Paiements → Situation des producteurs**.
6. Regroupez les achats en **lots**, fermez-les, puis enregistrez la **livraison**.

## Mode web (serveur)

Avec Docker :

```sh
docker build -t cacaocoop .
docker run -d -p 8000:8000 -v cacaocoop-data:/data \
  -e CACAO_SECRET_KEY="une-longue-cle-secrete" \
  -e CACAO_ALLOWED_HOSTS="coop.example.com" \
  -e CACAO_CSRF_ORIGINS="https://coop.example.com" \
  -e CACAO_HTTPS=1 \
  cacaocoop
docker exec -it <conteneur> python manage.py createsuperuser
```

Sans Docker : `pip install -r requirements-serveur.txt`, définissez les mêmes variables, puis
`python manage.py migrate && python manage.py init_coop && python manage.py collectstatic`
et lancez `gunicorn config.wsgi` derrière un serveur HTTPS (Nginx, Caddy…).

Pour utiliser PostgreSQL plutôt que SQLite : `CACAO_DB_ENGINE=postgresql` et `CACAO_DB_NAME`, `CACAO_DB_USER`,
`CACAO_DB_PASSWORD`, `CACAO_DB_HOST`, `CACAO_DB_PORT`. La liste complète des variables est en tête de
`config/settings.py`.

## Développement

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py init_coop --demo
.venv/bin/python manage.py createsuperuser
CACAO_DEBUG=1 .venv/bin/python manage.py runserver
.venv/bin/python manage.py test tests
```

Structure : `core` (coopérative, campagnes, sections, magasins, tableau de bord), `producteurs`, `achats`,
`paiements`, `stocks` ; gabarits HTML dans `templates/`, style dans `static/css/app.css` (aucune ressource
externe, pour fonctionner hors ligne).
