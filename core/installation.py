"""Assistant de première installation : remplace la création du compte en ligne de commande.

Tant qu'aucun administrateur n'existe, toutes les pages redirigent vers cet assistant.
"""

from datetime import date
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth import login, password_validation
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import Campagne, Cooperative, Magasin

_installe = False


def installation_terminee():
    global _installe
    if not _installe:
        _installe = User.objects.filter(is_superuser=True).exists()
    return _installe


class InstallationMiddleware:
    """Redirige vers l'assistant tant que le logiciel n'est pas configuré."""

    LIBRES = ("/installation/", "/static/", "/sw.js", "/manifest.webmanifest")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(self.LIBRES) and not installation_terminee():
            return redirect("core:installation")
        return self.get_response(request)


def debut_campagne(aujourd_hui):
    annee = aujourd_hui.year if aujourd_hui.month >= 10 else aujourd_hui.year - 1
    return date(annee, 10, 1)


class InstallationForm(forms.Form):
    # Coopérative
    nom = forms.CharField(label="Nom de la coopérative", max_length=200)
    sigle = forms.CharField(max_length=30, required=False)
    code_ccc = forms.CharField(label="Code coopérative (CCC)", max_length=60, required=False)
    numero_agrement = forms.CharField(label="N° d'agrément", max_length=60, required=False)
    region = forms.CharField(label="Région", max_length=100, required=False)
    departement = forms.CharField(label="Département", max_length=100, required=False)
    sous_prefecture = forms.CharField(label="Sous-préfecture", max_length=100, required=False)
    telephone = forms.CharField(label="Téléphone", max_length=40, required=False)
    # Administrateur
    identifiant = forms.CharField(label="Identifiant de l'administrateur", max_length=150, initial="admin")
    prenom = forms.CharField(label="Prénom", max_length=150, required=False)
    nom_famille = forms.CharField(label="Nom", max_length=150, required=False)
    mot_de_passe = forms.CharField(label="Mot de passe", widget=forms.PasswordInput,
                                   help_text="Au moins 8 caractères, pas uniquement des chiffres.")
    confirmation = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput)
    # Campagne et magasin
    campagne = forms.CharField(label="Campagne", max_length=60)
    date_debut = forms.DateField(label="Début de la campagne", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    date_fin = forms.DateField(label="Fin de la campagne", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    prix_kg = forms.DecimalField(label="Prix fixé bord champ (FCFA/kg)", min_value=0, decimal_places=2)
    magasin_code = forms.CharField(label="Code du magasin", max_length=20, initial="M01")
    magasin_nom = forms.CharField(label="Nom du magasin", max_length=100, initial="Magasin central")
    magasin_localite = forms.CharField(label="Localité du magasin", max_length=100, required=False)
    demo = forms.BooleanField(
        label="Ajouter des données d'exemple pour essayer le logiciel", required=False,
        help_text="À ne cocher que pour une démonstration : 20 producteurs fictifs, pesées, lots et expédition.",
    )

    def clean_identifiant(self):
        identifiant = self.cleaned_data["identifiant"].strip()
        if User.objects.filter(username=identifiant).exists():
            raise forms.ValidationError("Cet identifiant existe déjà.")
        return identifiant

    def clean(self):
        donnees = super().clean()
        mdp, conf = donnees.get("mot_de_passe"), donnees.get("confirmation")
        if mdp and conf and mdp != conf:
            self.add_error("confirmation", "Les deux mots de passe ne sont pas identiques.")
        elif mdp:
            try:
                password_validation.validate_password(mdp, User(username=donnees.get("identifiant", "")))
            except forms.ValidationError as e:
                self.add_error("mot_de_passe", e)
        if donnees.get("date_debut") and donnees.get("date_fin") and donnees["date_fin"] < donnees["date_debut"]:
            self.add_error("date_fin", "La fin doit être après le début.")
        return donnees


SECTIONS = [
    ("La coopérative", ["nom", "sigle", "code_ccc", "numero_agrement", "region", "departement", "sous_prefecture",
                        "telephone"]),
    ("Le compte administrateur", ["identifiant", "prenom", "nom_famille", "mot_de_passe", "confirmation"]),
    ("La campagne et le premier magasin", ["campagne", "date_debut", "date_fin", "prix_kg", "magasin_code",
                                           "magasin_nom", "magasin_localite"]),
    ("Essai", ["demo"]),
]


def assistant(request):
    if installation_terminee():
        return redirect("core:tableau_de_bord")
    debut = debut_campagne(date.today())
    form = InstallationForm(request.POST or None, initial={
        "campagne": f"{debut.year}-{debut.year + 1} principale",
        "date_debut": debut, "date_fin": date(debut.year + 1, 3, 31), "prix_kg": Decimal("2800"),
    })
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        with transaction.atomic():
            call_command("init_coop", verbosity=0)
            coop = Cooperative.objects.first() or Cooperative()
            for champ in ("nom", "sigle", "code_ccc", "numero_agrement", "region", "departement", "sous_prefecture",
                          "telephone"):
                setattr(coop, champ, d[champ])
            coop.save()
            if d["demo"]:
                call_command("init_coop", "--demo", verbosity=0)
                Cooperative.objects.filter(pk=coop.pk).update(nom=d["nom"], sigle=d["sigle"])
            else:
                Campagne.objects.create(libelle=d["campagne"], date_debut=d["date_debut"], date_fin=d["date_fin"],
                                        prix_kg=d["prix_kg"], active=True)
                Magasin.objects.get_or_create(code=d["magasin_code"], defaults={
                    "nom": d["magasin_nom"], "localite": d["magasin_localite"]})
            admin = User.objects.create_superuser(d["identifiant"], "", d["mot_de_passe"],
                                                  first_name=d["prenom"], last_name=d["nom_famille"])
            admin.groups.add(Group.objects.get(name="Administrateur"))
        login(request, admin, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Installation terminée. Bienvenue dans CacaoCoop ! Ajoutez maintenant vos "
                                  "producteurs, puis les programmes de certification (menu Certification).")
        return redirect(reverse("core:tableau_de_bord"))
    sections = [(titre, [form[c] for c in champs]) for titre, champs in SECTIONS]
    return render(request, "core/installation.html", {"form": form, "sections": sections})
