"""Sauvegarde de la base SQLite (mode bureau).

    python manage.py sauvegarde                  # copie dans ./sauvegardes/
    python manage.py sauvegarde --dossier E:\\    # copie sur une clé USB, par exemple
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Copie la base de données SQLite dans un fichier horodaté."

    def add_arguments(self, parser):
        parser.add_argument("--dossier", default=str(Path(settings.BASE_DIR) / "sauvegardes"))

    def handle(self, *args, **options):
        base = settings.DATABASES["default"]
        if base["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Cette commande ne concerne que SQLite. Pour PostgreSQL, utilisez pg_dump.")
        dossier = Path(options["dossier"])
        dossier.mkdir(parents=True, exist_ok=True)
        cible = dossier / f"cacaocoop_{datetime.now():%Y%m%d_%H%M%S}.sqlite3"
        with sqlite3.connect(base["NAME"]) as source, sqlite3.connect(cible) as destination:
            source.backup(destination)
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {cible}"))
