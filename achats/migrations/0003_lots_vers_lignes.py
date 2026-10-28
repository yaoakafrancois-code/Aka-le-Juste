"""Reprise des données : l'ancien lien achat → lot devient une ligne de lot ; tout l'existant est non certifié."""

from django.db import migrations
from django.db.models import F


def reprendre(apps, schema_editor):
    Achat = apps.get_model("achats", "Achat")
    LigneLot = apps.get_model("stocks", "LigneLot")
    Achat.objects.update(poids_certifie=0, poids_non_certifie=F("poids_net"))
    LigneLot.objects.bulk_create([
        LigneLot(lot_id=a.lot_id, achat_id=a.pk, certifie=False, poids=a.poids_net, sacs=a.nombre_sacs)
        for a in Achat.objects.filter(lot__isnull=False)
    ])


class Migration(migrations.Migration):
    dependencies = [
        ("achats", "0002_remove_achat_lot_achat_montant_prime_and_more"),
        ("stocks", "0002_remove_livraison_numero_bordereau_and_more"),
    ]

    operations = [
        migrations.RunPython(reprendre, migrations.RunPython.noop),
        migrations.RemoveField(model_name="achat", name="lot"),
    ]
