"""Lance CacaoCoop en mode bureau (un ordinateur, sans internet).

    python lancer.py              # http://127.0.0.1:8000, ouvre le navigateur
    python lancer.py --reseau     # accessible depuis les autres postes du réseau local
    python lancer.py --port 8080

Au premier lancement, la base de données est créée et un compte administrateur est demandé.
"""

import argparse
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def adresse_locale():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="CacaoCoop – mode bureau")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reseau", action="store_true", help="Ouvrir l'accès aux autres postes du réseau local.")
    parser.add_argument("--sans-navigateur", action="store_true")
    args = parser.parse_args()

    hote = "0.0.0.0" if args.reseau else "127.0.0.1"
    if args.reseau:
        os.environ.setdefault("CACAO_ALLOWED_HOSTS", "*")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django
    from django.core.management import call_command

    django.setup()
    call_command("migrate", verbosity=0)
    call_command("init_coop", verbosity=0)

    from django.contrib.auth.models import User

    if not User.objects.filter(is_superuser=True).exists():
        print("\nPremier lancement : création du compte administrateur.")
        call_command("createsuperuser")

    from waitress import serve

    from config.wsgi import application

    url = f"http://127.0.0.1:{args.port}/"
    print(f"\nCacaoCoop est démarré : {url}")
    if args.reseau:
        print(f"Depuis les autres postes du réseau : http://{adresse_locale()}:{args.port}/")
    print("Fermez cette fenêtre (ou Ctrl+C) pour arrêter.\n")
    if not args.sans_navigateur:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    serve(application, host=hote, port=args.port, threads=8)


if __name__ == "__main__":
    main()
