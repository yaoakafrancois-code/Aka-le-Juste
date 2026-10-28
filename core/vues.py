"""Briques communes aux vues de l'application (listes, formulaires, exports CSV)."""

import csv

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import ProtectedError, Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic import CreateView, DeleteView, ListView, UpdateView


class FormulaireStyle(forms.ModelForm):
    """ModelForm avec champs de date au format HTML5 et classes CSS."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            if isinstance(champ, forms.DateField):
                champ.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
            elif isinstance(champ.widget, forms.Textarea):
                champ.widget.attrs["rows"] = 3


def permission(modele, action):
    return f"{modele._meta.app_label}.{action}_{modele._meta.model_name}"


class AccesMixin(LoginRequiredMixin, PermissionRequiredMixin):
    action = "view"

    def get_permission_required(self):
        return [permission(self.model, self.action)]


class Liste(AccesMixin, ListView):
    """Liste paginée avec recherche plein texte (paramètre ?q=) et filtres simples."""

    paginate_by = 25
    champs_recherche = ()
    filtres = ()  # noms de paramètres GET appliqués tels quels (ex. "campagne", "magasin")

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q and self.champs_recherche:
            condition = Q()
            for champ in self.champs_recherche:
                condition |= Q(**{f"{champ}__icontains": q})
            qs = qs.filter(condition)
        for nom in self.filtres:
            valeur = self.request.GET.get(nom)
            if valeur:
                qs = qs.filter(**{nom: valeur})
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["params"] = params.urlencode()
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class FormulaireMixin(AccesMixin):
    template_name = "form.html"
    titre = ""
    message = "Enregistrement effectué."

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["titre"] = self.titre or (
            f"Modifier {self.object}" if getattr(self, "object", None) else f"Nouveau {self.model._meta.verbose_name}"
        )
        return ctx

    def form_valid(self, form):
        if hasattr(form.instance, "agent_id") and not form.instance.agent_id:
            form.instance.agent = self.request.user
        reponse = super().form_valid(form)
        messages.success(self.request, self.message)
        return reponse


class Creation(FormulaireMixin, CreateView):
    action = "add"


class Modification(FormulaireMixin, UpdateView):
    action = "change"


class Suppression(AccesMixin, DeleteView):
    action = "delete"
    template_name = "confirmer_suppression.html"

    def form_valid(self, form):
        try:
            reponse = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "Suppression impossible : cet élément est utilisé ailleurs.")
            return redirect(self.request.path)
        messages.success(self.request, "Suppression effectuée.")
        return reponse


def reponse_csv(nom_fichier, entetes, lignes):
    """Export CSV lisible par Excel (UTF-8 avec BOM, séparateur point-virgule)."""
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="{nom_fichier}"'
    reponse.write("﻿")
    writer = csv.writer(reponse, delimiter=";")
    writer.writerow(entetes)
    for ligne in lignes:
        writer.writerow(ligne)
    return reponse
