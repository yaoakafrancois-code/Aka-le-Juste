"""Lance CacaoCoop en mode bureau (un ordinateur, sans internet).

    python lancer.py              # http://127.0.0.1:8000, ouvre le navigateur
    python lancer.py --reseau     # accessible depuis les autres postes du réseau local
    python lancer.py --port 8080

Au premier lancement, la base de données est créée et le navigateur ouvre l'assistant d'installation.
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


def port_occupe(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    parser = argparse.ArgumentParser(description="CacaoCoop – mode bureau")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reseau", action="store_true", help="Ouvrir l'accès aux autres postes du réseau local.")
    parser.add_argument("--sans-navigateur", action="store_true")
    args = parser.parse_args()

    if port_occupe(args.port):
        # CacaoCoop (ou un autre programme) utilise déjà ce port : on ouvre simplement le navigateur.
        print(f"CacaoCoop semble déjà ouvert sur ce port : ouverture de http://127.0.0.1:{args.port}/")
        print("Si la page ne s'affiche pas, fermez l'autre fenêtre CacaoCoop ou utilisez --port 8001.")
        if not args.sans_navigateur:
            webbrowser.open(f"http://127.0.0.1:{args.port}/")
        return

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

    premier_lancement = not User.objects.filter(is_superuser=True).exists()
    from waitress import serve

    from config.wsgi import application

    url = f"http://127.0.0.1:{args.port}/"
    print(f"\nCacaoCoop est démarré : {url}")
    if args.reseau:
        print(f"Depuis les autres postes du réseau : http://{adresse_locale()}:{args.port}/")
    if premier_lancement:
        print("Premier lancement : terminez l'installation dans le navigateur qui s'ouvre.")
    print("Fermez cette fenêtre (ou Ctrl+C) pour arrêter.\n")
    if not args.sans_navigateur:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    serve(application, host=hote, port=args.port, threads=8)


if __name__ == "__main__":
    main()
