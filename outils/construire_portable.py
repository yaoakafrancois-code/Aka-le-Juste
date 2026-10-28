"""Fabrique la version portable de CacaoCoop pour Windows (clé USB, disque dur, CD).

    python outils/construire_portable.py                   # produit dist/CacaoCoop-portable-windows.zip
    python outils/construire_portable.py --installateur    # + dist/Installer-CacaoCoop.exe (nécessite NSIS)

Le dossier obtenu contient son propre Python (paquet officiel « python » publié sur NuGet) et
toutes les dépendances : il fonctionne sur n'importe quel Windows 10/11 64 bits, sans installation
et sans internet. Le script peut tourner sous Linux, macOS ou Windows (dépendances 100 % Python).
"""

import argparse
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
VERSION = (RACINE / "VERSION").read_text(encoding="ascii").strip()
VERSION_PYTHON = "3.12.8"
URL_NUGET = "https://api.nuget.org/v3-flatcontainer/python/{v}/python.{v}.nupkg"
A_COPIER = ["config", "core", "producteurs", "achats", "paiements", "stocks", "templates", "static",
            "manage.py", "lancer.py", "requirements.txt", "README.md", "VERSION"]
# Parties de la bibliothèque standard inutiles ici (allège le dossier d'environ 40 %).
A_RETIRER = ["Lib/test", "Lib/idlelib", "Lib/tkinter", "Lib/turtledemo", "Lib/ensurepip", "tcl",
             "DLLs/_tkinter.pyd", "DLLs/tcl86t.dll", "DLLs/tk86t.dll"]

LANCEURS = {
    "CacaoCoop.bat": r"""@echo off
title CacaoCoop
cd /d "%~dp0"
"python\python.exe" lancer.py %*
if errorlevel 1 pause
""",
    "CacaoCoop - reseau (tablettes).bat": r"""@echo off
title CacaoCoop (reseau local)
cd /d "%~dp0"
echo Les tablettes et telephones connectes au meme Wi-Fi pourront ouvrir l'adresse affichee ci-dessous.
"python\python.exe" lancer.py --reseau
pause
""",
    "Sauvegarder les donnees.bat": r"""@echo off
cd /d "%~dp0"
"python\python.exe" manage.py sauvegarde
pause
""",
    "Installer sur cet ordinateur.bat": r"""@echo off
REM Copie CacaoCoop dans le dossier de l'utilisateur et cree un raccourci sur le bureau.
set CIBLE=%LOCALAPPDATA%\CacaoCoop
echo Installation de CacaoCoop dans %CIBLE% ...
robocopy "%~dp0." "%CIBLE%" /E /XD data sauvegardes /NFL /NDL /NJH /NJS >nul
if not exist "%CIBLE%\data" if exist "%~dp0data" robocopy "%~dp0data" "%CIBLE%\data" /E /NFL /NDL /NJH /NJS >nul
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\CacaoCoop.lnk');$s.TargetPath='%CIBLE%\CacaoCoop.bat';$s.WorkingDirectory='%CIBLE%';$s.IconLocation='%CIBLE%\python\python.exe';$s.Save()"
echo Termine. Un raccourci CacaoCoop a ete cree sur le bureau.
pause
""",
}

LISEZMOI = """CacaoCoop - version portable pour Windows
==========================================

Aucune installation n'est nécessaire. Ce dossier peut être copié sur une clé USB, un disque dur
externe ou un CD (pour un CD, copiez d'abord le dossier sur l'ordinateur : il faut pouvoir écrire
les données).

  CacaoCoop.bat                         Démarre le logiciel sur cet ordinateur.
  CacaoCoop - reseau (tablettes).bat    Démarre le logiciel et l'ouvre aux tablettes / téléphones
                                        Android connectés au même Wi-Fi.
  Installer sur cet ordinateur.bat      Copie le logiciel sur l'ordinateur et crée un raccourci
                                        sur le bureau.
  Sauvegarder les donnees.bat           Copie la base de données dans le dossier « sauvegardes ».

Au premier démarrage, choisissez un identifiant et un mot de passe administrateur. Le navigateur
s'ouvre ensuite automatiquement.

Les données sont enregistrées dans le dossier « data ». Si vous lancez le logiciel depuis la clé
USB, les données restent sur la clé : sauvegardez-les régulièrement. Un seul ordinateur à la fois
doit utiliser une même base de données.

Sur tablette ou téléphone Android : lancez « CacaoCoop - reseau (tablettes).bat » sur l'ordinateur,
ouvrez Chrome sur la tablette à l'adresse affichée (ex. http://192.168.1.10:8000), puis menu
⋮ > « Ajouter à l'écran d'accueil ». Si Windows le demande, autorisez l'accès au réseau privé.
"""


def telecharger(url, destination):
    if destination.exists():
        return destination
    print(f"Téléchargement de {url}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as reponse, open(destination, "wb") as f:
        shutil.copyfileobj(reponse, f)
    return destination


def construire(version, sortie, paquet_python=None):
    dossier = sortie / "CacaoCoop"
    if dossier.exists():
        shutil.rmtree(dossier)
    (dossier / "python").mkdir(parents=True)

    nupkg = Path(paquet_python) if paquet_python else telecharger(
        URL_NUGET.format(v=version), RACINE / "dist" / "cache" / f"python.{version}.nupkg")
    print("Extraction de Python…")
    with zipfile.ZipFile(nupkg) as z:
        for nom in z.namelist():
            if nom.startswith("tools/") and not nom.endswith("/"):
                cible = dossier / "python" / nom[len("tools/"):]
                cible.parent.mkdir(parents=True, exist_ok=True)
                with z.open(nom) as src, open(cible, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    for chemin in A_RETIRER:
        p = dossier / "python" / chemin
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

    print("Installation des dépendances (Django, Waitress, WhiteNoise)…")
    majeure = ".".join(version.split(".")[:2])
    subprocess.run([
        sys.executable, "-m", "pip", "install", "--quiet", "--no-compile", "--disable-pip-version-check",
        "-r", str(RACINE / "requirements.txt"), "--target", str(dossier / "python" / "Lib" / "site-packages"),
        "--platform", "win_amd64", "--python-version", majeure, "--implementation", "cp",
        "--only-binary=:all:",
    ], check=True)

    print("Copie de l'application…")
    ignorer = shutil.ignore_patterns("__pycache__", "*.pyc")
    for nom in A_COPIER:
        src = RACINE / nom
        if src.is_dir():
            shutil.copytree(src, dossier / nom, ignore=ignorer)
        else:
            shutil.copy2(src, dossier / nom)
    for nom, contenu in LANCEURS.items():
        (dossier / nom).write_text(contenu.replace("\n", "\r\n"), encoding="ascii")
    (dossier / "LISEZMOI.txt").write_text(LISEZMOI.replace("\n", "\r\n"), encoding="utf-8-sig")
    guide = (RACINE / "GUIDE_INSTALLATION.md").read_text(encoding="utf-8")
    (dossier / "GUIDE_INSTALLATION.txt").write_text(guide.replace("\n", "\r\n"), encoding="utf-8-sig")
    (dossier / "VERSION.txt").write_text(VERSION + "\r\n", encoding="ascii")

    archive = sortie / "CacaoCoop-portable-windows.zip"
    print(f"Création de {archive}…")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for fichier in sorted(dossier.rglob("*")):
            if fichier.is_file():
                z.write(fichier, fichier.relative_to(sortie))
    taille = archive.stat().st_size / 1024 / 1024
    print(f"Terminé : {archive} ({taille:.0f} Mo)")
    return archive


def construire_installateur(sortie):
    """Compile l'installateur Windows avec NSIS (makensis, disponible sous Linux, macOS et Windows)."""
    makensis = shutil.which("makensis")
    if not makensis:
        sys.exit("NSIS introuvable : installez-le (apt install nsis, choco install nsis…) puis relancez.")
    exe = sortie / "Installer-CacaoCoop.exe"
    subprocess.run([
        makensis, "-V2", f"-DVERSION={VERSION}", f"-DSOURCE={sortie / 'CacaoCoop'}", f"-DSORTIE={exe}",
        str(RACINE / "outils" / "installateur.nsi"),
    ], check=True)
    print(f"Terminé : {exe} ({exe.stat().st_size / 1024 / 1024:.0f} Mo)")
    return exe


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version-python", default=VERSION_PYTHON)
    parser.add_argument("--sortie", default=str(RACINE / "dist"))
    parser.add_argument("--paquet-python", help="Fichier python.X.Y.Z.nupkg déjà téléchargé (hors ligne).")
    parser.add_argument("--installateur", action="store_true", help="Produire aussi l'installateur Windows (.exe).")
    args = parser.parse_args()
    construire(args.version_python, Path(args.sortie), args.paquet_python)
    if args.installateur:
        construire_installateur(Path(args.sortie))
