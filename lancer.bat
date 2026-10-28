@echo off
REM Lancement de CacaoCoop sous Windows (double-cliquer sur ce fichier).
cd /d "%~dp0"
if not exist .venv (
    echo Installation initiale, veuillez patienter...
    python -m venv .venv || goto erreur
    .venv\Scripts\python -m pip install -r requirements.txt || goto erreur
)
.venv\Scripts\python lancer.py %*
pause
exit /b

:erreur
echo Erreur : verifiez que Python 3.11 ou plus recent est installe (https://www.python.org).
pause
