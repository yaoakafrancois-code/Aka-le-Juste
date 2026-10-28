# Guide d'installation de CacaoCoop

CacaoCoop s'installe sur **un ordinateur Windows** de la coopérative (le « poste principal »), qui garde toutes
les données. Les **tablettes et smartphones Android** se connectent à ce poste par le Wi-Fi de la coopérative.

Les fichiers se téléchargent sur la page **Releases** du dépôt GitHub (dernière version) :

| Fichier | Pour quoi faire |
|---|---|
| `Installer-CacaoCoop.exe` | Installer le logiciel sur un ordinateur Windows 10 ou 11 (64 bits) |
| `CacaoCoop-portable-windows.zip` | Utiliser le logiciel depuis une clé USB ou un disque dur, sans installation |
| `CacaoCoop-android.apk` | Installer l'application sur une tablette ou un smartphone Android (version 7 ou plus récente) |

## 1. Installer sur l'ordinateur principal

1. Double-cliquez sur `Installer-CacaoCoop.exe`.
   Si Windows affiche « Windows a protégé votre ordinateur », cliquez sur **Informations complémentaires**,
   puis sur **Exécuter quand même**. Le logiciel n'est pas signé numériquement, d'où cet avertissement.
2. Suivez l'assistant (Suivant → Installer → Terminer). Aucun droit administrateur n'est nécessaire.
3. CacaoCoop démarre et le navigateur s'ouvre sur l'**assistant de première installation** :
   - le nom de la coopérative, son code CCC, sa région ;
   - l'identifiant et le mot de passe de l'administrateur : **notez-les** ;
   - la campagne, avec ses dates et le prix fixé bord champ ;
   - le premier magasin.
4. Cliquez sur **Terminer l'installation**. Le tableau de bord s'affiche : le logiciel est prêt.

Ensuite, CacaoCoop se lance avec l'icône **CacaoCoop** du bureau. Une fenêtre noire s'ouvre en même temps que le
navigateur : **ne la fermez pas** pendant le travail. La fermer arrête le logiciel.

## 2. Premiers réglages

Dans le menu **Paramètres** (réservé à l'administrateur) :

1. **Programmes de certification** : RA et ARS 1000 sont déjà créés. Renseignez pour chacun le n° de certificat de la
   coopérative, la prime producteur (FCFA/kg) et le rendement maximum de la norme (1 000 kg/ha par défaut).
2. **Utilisateurs** : créez un compte par personne (peseurs, comptable, magasinier) et donnez-leur un **groupe** :
   Agent d'achat, Comptable, Magasinier ou Administrateur.
3. **Sections**, **magasins** et **exportateurs**.
4. **Prix du jour**, si le prix change en cours de campagne.

Puis, dans le logiciel : enregistrez les **producteurs**, avec leur n° de carte et leurs parcelles, et
**certifiez-les** (bouton « + Certification » sur la fiche du producteur).

## 3. Tablettes et smartphones Android

Sur l'ordinateur principal, lancez **CacaoCoop - réseau (tablettes)** (menu Démarrer → CacaoCoop).
La fenêtre affiche l'adresse à utiliser, par exemple `http://192.168.1.10:8000`.
La première fois, Windows demande d'autoriser l'accès au réseau : cochez **Réseaux privés** et validez.

Sur chaque tablette :

1. Copiez `CacaoCoop-android.apk` sur la tablette (câble USB, WhatsApp, e-mail…) et ouvrez-le.
   Android demande d'**autoriser l'installation d'applications inconnues** : acceptez pour cette source.
2. Ouvrez l'application **CacaoCoop**, tapez l'adresse affichée sur l'ordinateur, puis **Se connecter**.
3. Connectez-vous avec le compte du peseur.

Au champ, sans réseau, utilisez **Achats → Collecte terrain**. Avant de partir, ouvrez cette page avec le réseau
pour copier les producteurs sur la tablette. Les pesées sont gardées sur la tablette, puis envoyées toutes seules
au retour du Wi-Fi. Laissez l'application ouverte, ou en arrière-plan, pendant la collecte.

Sans l'application, la tablette peut aussi ouvrir l'adresse dans Chrome.

## 4. Sauvegardes (très important)

Toutes les données sont sur l'ordinateur principal, dans le dossier `data` de l'installation. Faites une sauvegarde
**au moins chaque semaine**, sur une clé USB :

- menu Démarrer → CacaoCoop → **Sauvegarder les données**. La copie va dans le dossier `sauvegardes` ;
- copiez ensuite ce dossier sur une clé USB, que vous rangez ailleurs que l'ordinateur.

## 5. Mise à jour et désinstallation

- **Mettre à jour** : lancez le nouveau `Installer-CacaoCoop.exe`. Les données sont conservées. Faites quand même
  une sauvegarde avant.
- **Désinstaller** : Paramètres Windows → Applications → CacaoCoop → Désinstaller. Les dossiers `data` et
  `sauvegardes` sont conservés. Supprimez-les vous-même seulement si vous êtes sûr de ne plus en avoir besoin.

## Problèmes fréquents

| Problème | Solution |
|---|---|
| Le navigateur ne s'ouvre pas | Ouvrez-le vous-même à l'adresse `http://127.0.0.1:8000` |
| « Le port est déjà utilisé » | CacaoCoop est déjà ouvert : cherchez sa fenêtre noire dans la barre des tâches |
| La tablette n'arrive pas à se connecter | Même Wi-Fi que l'ordinateur ? Lancé avec « réseau (tablettes) » ? Accès réseau autorisé par Windows ? |
| Mot de passe administrateur oublié | Dans le dossier d'installation : `python\python.exe manage.py changepassword <identifiant>` |
