"""
Configuration de CacaoCoop.

Deux modes de fonctionnement :
- Bureau (par défaut) : un seul ordinateur, base SQLite locale, aucun accès internet requis.
- Web (serveur) : définir les variables d'environnement ci-dessous.

Variables d'environnement :
    CACAO_SECRET_KEY     clé secrète (obligatoire en mode web)
    CACAO_DEBUG          "1" pour activer le mode debug
    CACAO_ALLOWED_HOSTS  liste séparée par des virgules (ex. "coop.example.com")
    CACAO_CSRF_ORIGINS   origines de confiance (ex. "https://coop.example.com")
    CACAO_DB_ENGINE      "postgresql" pour utiliser PostgreSQL (SQLite sinon)
    CACAO_DB_NAME, CACAO_DB_USER, CACAO_DB_PASSWORD, CACAO_DB_HOST, CACAO_DB_PORT
    CACAO_DATA_DIR       dossier de la base SQLite (par défaut : ./data)
    CACAO_HTTPS          "1" si le site est servi en HTTPS (cookies sécurisés)
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("CACAO_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.environ.get(
    "CACAO_SECRET_KEY",
    "cle-locale-a-remplacer-en-production-0f6c1d9a",
)
DEBUG = os.environ.get("CACAO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("CACAO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("CACAO_CSRF_ORIGINS", "").split(",") if o.strip()
]

if os.environ.get("CACAO_HTTPS") == "1":
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "producteurs",
    "achats",
    "paiements",
    "stocks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "core.installation.InstallationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.cooperative",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if os.environ.get("CACAO_DB_ENGINE") == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("CACAO_DB_NAME", "cacaocoop"),
            "USER": os.environ.get("CACAO_DB_USER", "cacaocoop"),
            "PASSWORD": os.environ.get("CACAO_DB_PASSWORD", ""),
            "HOST": os.environ.get("CACAO_DB_HOST", "localhost"),
            "PORT": os.environ.get("CACAO_DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DATA_DIR / "cacaocoop.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Abidjan"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT.mkdir(exist_ok=True)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
# Permet de servir les fichiers statiques sans « collectstatic » en mode bureau.
WHITENOISE_USE_FINDERS = True

# Pièces justificatives (augmentations de quota) : stockées avec les données, servies après connexion.
MEDIA_ROOT = DATA_DIR / "pieces"
MEDIA_URL = "/pieces/"
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "core:tableau_de_bord"
LOGOUT_REDIRECT_URL = "login"
