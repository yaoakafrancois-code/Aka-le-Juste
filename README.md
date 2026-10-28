# CacaoCoop – Gestion des achats et de la collecte de cacao

Logiciel de gestion pour les coopératives cacaoyères : producteurs et parcelles, pesées et achats bord champ,
paiements et avances, stocks, lots et livraisons aux exportateurs, avec traçabilité jusqu'à la parcelle (EUDR).

Il fonctionne de deux façons, avec le même code :

- **Mode bureau** : sur un seul ordinateur de la coopérative, sans internet (base SQLite locale). Les autres postes
  du même réseau local peuvent s'y connecter avec leur navigateur.
- **Mode web** : sur un serveur, accessible depuis n'importe où (ordinateur, tablette, téléphone).
- **Version portable Windows** : un dossier à copier sur une clé USB, un disque dur ou un CD, qui contient
  son propre Python. Rien à installer.
- **Tablette et smartphone Android** : l'interface s'adapte aux petits écrans et s'installe sur l'écran
  d'accueil. La tablette se connecte à l'ordinateur de la coopérative par le Wi-Fi, ou au serveur web.

## Fonctionnalités

| Module | Ce qu'il fait |
|---|---|
| **Producteurs et parcelles** | Fiche producteur (identité, section, village, carte producteur), parcelles avec superficie, GPS, polygone GeoJSON, certification et statut EUDR. Export CSV de traçabilité. |
| **Certification (RA, ARS 1000)** | Programmes de certification avec rendement de référence et prime par kg. Statut de chaque producteur par campagne (certifié, en conversion, suspendu, exclu), n° de membre, niveau ARS 1000, dates d'inspection interne et d'audit. Suivi du volume certifiable (production estimée), acheté et restant. Liste des membres pour les audits (CSV). |
| **Achats et pesées** | Saisie de la pesée : sacs, poids brut, tare, humidité, réfaction, qualité. Le logiciel applique le **prix du jour** s'il existe, sinon le **prix fixé** de la campagne. Il répartit automatiquement le poids entre **certifié** et **non certifié** et calcule la prime de certification. Reçu d'achat imprimable. |
| **Paiements et avances** | Paiements (espèces, Mobile Money, chèque, virement), avances (pré-financement), primes (certification, qualité, ristourne). Situation de tous les producteurs (qui payer, qui doit encore une avance), relevé de compte imprimable. Un paiement ne peut pas dépasser le solde dû. |
| **Stocks, lots et connaissements** | Stock par magasin (certifié / non certifié). Lots séparés : certifié RA, certifié ARS 1000 ou conventionnel, sans mélange. Analyse qualité (humidité, grainage, moisies, ardoisées, défauts) avec grade calculé. Expédition à l'exportateur avec **connaissement / fiche de suivi** imprimable (4 exemplaires), annexe de traçabilité des producteurs, export CSV pour la saisie dans le système du Conseil du Café-Cacao, poids reconnu à l'arrivée et écart. |
| **Tableau de bord et rapports** | Tonnage acheté, montants, reste à payer, stock, achats par mois, par section, par magasin, par qualité, meilleurs producteurs. |
| **Utilisateurs et rôles** | Administrateur, Agent d'achat, Comptable, Magasinier, chacun avec ses droits. |

Calculs utilisés :

- Poids net = (poids brut − tare) × (1 − réfaction %)
- Prix = prix du jour du magasin, sinon prix du jour général, sinon prix fixé de la campagne (ou prix saisi)
- Montant = poids net × prix au kg (arrondi au franc)
- Volume certifiable d'un producteur = production estimée saisie, sinon superficie certifiée × rendement de référence
- Poids certifié = min(poids net, volume certifiable restant) ; le reste est non certifié
- Prime de certification = poids certifié × prime du programme (FCFA/kg)
- Solde producteur = achats + primes − paiements − avances (positif : la coopérative doit payer ; négatif : avance à récupérer)

Exemple : le producteur X a 3 ha certifiés RA et le rendement de référence est de 500 kg/ha, soit 1 500 kg
certifiables. Il livre 500 kg à 2 800 F/kg : le reçu indique 500 kg certifiés RA, 1 400 000 F pour le cacao
et la prime RA. Quand il dépasse 1 500 kg sur la campagne, le surplus est automatiquement acheté comme non certifié.

### Normes et documents officiels

- **Rainforest Alliance et ARS 1000** : le logiciel tient la liste des membres, leur statut, la superficie et
  la production estimée, et empêche de vendre plus de cacao certifié que le volume estimé. La ségrégation des
  lots et la traçabilité vont jusqu'à la parcelle (GPS, polygone). Les exigences propres à chaque norme
  (formations, travail des enfants, environnement…) restent gérées par le Système de Gestion Interne.
- **Connaissement (Conseil du Café-Cacao)** : le document imprimé reprend les informations de la fiche de
  suivi : coopérative (code CCC, agrément, région / département / sous-préfecture), exportateur, destination,
  produit, type, grade, sacs, poids, transport, chauffeur et réception. Le n° de connaissement est celui délivré
  par le CCC. L'export « Export pour le CCC (CSV) » facilite la saisie dans la plateforme du CCC.
  **Le modèle officiel peut évoluer** : envoyez-nous un exemplaire vierge pour aligner exactement la mise en page.
- **Grades** : seuils ISO 2451 (Grade I : moisies ≤ 3 %, ardoisées ≤ 3 %, défauts ≤ 3 % ; Grade II : ≤ 4 %,
  ≤ 8 %, ≤ 6 % ; humidité ≤ 8 %), à confirmer avec la réglementation en vigueur.

## Version portable (clé USB, disque dur)

1. Récupérez `CacaoCoop-portable-windows.zip`, soit dans l'onglet **Actions** du dépôt GitHub (artefact
   « CacaoCoop-portable-windows » produit à chaque modification), soit en le fabriquant vous-même avec
   `python outils/construire_portable.py`.
2. Décompressez-le sur la clé USB ou le disque : vous obtenez un dossier `CacaoCoop`.
3. Double-cliquez sur `CacaoCoop.bat`. Pour l'installer sur un ordinateur, utilisez
   `Installer sur cet ordinateur.bat` : il copie le dossier et crée un raccourci sur le bureau.

Le fichier `LISEZMOI.txt` du dossier explique chaque lanceur.

## Tablettes et smartphones Android

1. Sur l'ordinateur de la coopérative, lancez `CacaoCoop - reseau (tablettes).bat` (ou `lancer.py --reseau`).
   L'adresse à utiliser s'affiche, par exemple `http://192.168.1.10:8000`.
2. Sur la tablette, connectée au **même Wi-Fi**, ouvrez cette adresse dans Chrome.
3. Menu ⋮ → **Ajouter à l'écran d'accueil** : CacaoCoop s'ouvre ensuite comme une application.

Avec le mode web (serveur en HTTPS), la tablette fonctionne partout où il y a une connexion internet.
Si la connexion est coupée, une page l'indique. La saisie entièrement hors ligne, avec synchronisation
ultérieure, est prévue dans une prochaine version.

## Mode bureau depuis les sources (développeurs)

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

1. Menu **Paramètres** : renseignez la coopérative (dont le code CCC), créez la **campagne** (dates et prix fixé)
   et cochez « active », puis les **sections**, les **magasins** et les **exportateurs**.
   Le cas échéant, saisissez les **prix du jour** (menu Achats → Prix du jour).
2. Dans **Certification → Programmes et primes**, complétez RA et ARS 1000 (créés automatiquement) : n° de certificat,
   rendement de référence (kg/ha) et prime producteur (FCFA/kg). Certifiez ensuite les producteurs pour la campagne
   (bouton « + Certification » sur leur fiche).
3. Créez les comptes utilisateurs dans **Paramètres → Utilisateurs** et attribuez-leur un groupe (rôle).
   Cochez « statut équipe » pour les administrateurs qui doivent accéder aux paramètres.
4. Enregistrez les **producteurs** et leurs **parcelles**.
5. Saisissez les **pesées** (menu Achats → Nouvelle pesée), imprimez le reçu.
6. Payez les producteurs depuis **Paiements → Situation des producteurs**.
7. Créez des **lots** par type (certifié RA, ARS 1000 ou conventionnel), ajoutez-y les achats, saisissez
   l'analyse qualité, puis fermez le lot.
8. Enregistrez l'**expédition** (n° de connaissement, camion, chauffeur) et imprimez le **connaissement**.

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

Structure : `core` (coopérative, campagnes, prix du jour, sections, magasins, tableau de bord, application
installable), `producteurs` (dont programmes et certifications), `achats`,
`paiements`, `stocks` ; gabarits HTML dans `templates/`, style dans `static/css/app.css` (aucune ressource
externe, pour fonctionner hors ligne).
