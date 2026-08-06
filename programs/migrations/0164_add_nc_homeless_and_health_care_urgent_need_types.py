# Generated manually to add NC-only urgent need types for:
# MFB-1310: NC - Add two new urgent need types to NC white label:
#   Homeless Services & Free/Low-Cost Medical Care
#
# This creates two new UrgentNeedType rows scoped to the "nc" white label only
# (Colorado and other white labels are untouched), following the existing NC
# naming convention (external_name prefixed with "nc_", name prefixed with
# "[North Carolina] "). It also ensures the CategoryIconName rows referenced
# by the icon field ("homeless_services" and "free_health_care") exist -- these
# names match the keys already present in the frontend's ICON_NAME_MAP
# (benefits-calculator/src/Components/Results/helpers.ts).

from django.db import migrations

NC_WHITE_LABEL_CODE = "nc"

NEW_URGENT_NEED_TYPES = [
    {
        "external_name": "nc_homeless_services",
        "icon_name": "homeless_services",
        "name_text": "[North Carolina] Homeless services",
    },
    {
        "external_name": "nc_free_low_cost_medical_care",
        "icon_name": "free_health_care",
        "name_text": "[North Carolina] Free/low-cost medical care",
    },
]


def add_urgent_need_types(apps, schema_editor):
    UrgentNeedType = apps.get_model("programs", "UrgentNeedType")
    CategoryIconName = apps.get_model("programs", "CategoryIconName")
    Translation = apps.get_model("translations", "Translation")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    white_label = WhiteLabel.objects.filter(code=NC_WHITE_LABEL_CODE).first()
    if white_label is None:
        # NC white label not present in this environment (e.g. some test DBs); skip.
        return

    for entry in NEW_URGENT_NEED_TYPES:
        if UrgentNeedType.objects.filter(
            white_label=white_label, external_name=entry["external_name"]
        ).exists():
            continue

        icon, _ = CategoryIconName.objects.get_or_create(name=entry["icon_name"])

        translation = Translation.objects.add_translation(
            f"urgent_need_type.{entry['external_name']}_temporary_key-name",
            default_message=entry["name_text"],
        )

        urgent_need_type = UrgentNeedType.objects.create(
            external_name=entry["external_name"],
            icon=icon,
            white_label=white_label,
            name=translation,
        )

        translation.label = f"urgent_need_type.{entry['external_name']}_{urgent_need_type.id}-name"
        translation.save()


def remove_urgent_need_types(apps, schema_editor):
    UrgentNeedType = apps.get_model("programs", "UrgentNeedType")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    white_label = WhiteLabel.objects.filter(code=NC_WHITE_LABEL_CODE).first()
    if white_label is None:
        return

    UrgentNeedType.objects.filter(
        white_label=white_label,
        external_name__in=[entry["external_name"] for entry in NEW_URGENT_NEED_TYPES],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0163_drop_program_value_type"),
        ("screener", "0001_initial"),
        ("translations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_urgent_need_types, remove_urgent_need_types),
    ]
