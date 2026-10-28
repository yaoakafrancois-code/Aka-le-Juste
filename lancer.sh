#!/bin/sh
# Lancement de CacaoCoop sous Linux / macOS.
cd "$(dirname "$0")" || exit 1
if [ ! -d .venv ]; then
    echo "Installation initiale, veuillez patienter..."
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt || exit 1
fi
exec .venv/bin/python lancer.py "$@"
