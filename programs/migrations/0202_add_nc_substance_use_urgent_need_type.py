# Generated manually to add an NC-only urgent need type for the new
# "Help with drug or alcohol use" category, requested in a young-adults feedback
# session by a young adult who works in the drug/alcohol rehab support community.
#
# This creates one new UrgentNeedType row scoped to the "nc" white label only
# (other white labels are untouched), following the existing NC naming convention
# for external_name (prefixed with "nc_"). Unlike the precedent categories
# (0165_add_nc_homeless_and_health_care_urgent_need_types.py), `name_text` is NOT
# prefixed with "[North Carolina] ": that prefix is meant to disambiguate rows
# across white labels in the Django admin, but `name` is also what the results
# page renders as the public-facing category heading above matching resource
# cards -- on NC's own white-labeled site, prepending "[North Carolina]" to every
# heading is redundant, since the whole site is already NC-scoped. This also
# ensures the CategoryIconName row referenced by the icon field ("drug_alcohol_use")
# exists -- this name matches the key added to the frontend's ICON_NAME_MAP
# (benefits-calculator/src/Components/Results/helpers.ts).

from django.db import migrations

NC_WHITE_LABEL_CODE = "nc"

NEW_URGENT_NEED_TYPES = [
    {
        "external_name": "nc_drug_alcohol_use",
        "icon_name": "drug_alcohol_use",
        "name_text": "Help with drug or alcohol use",
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
        ("programs", "0201_move_state_wic_current_benefits"),
        ("screener", "0001_initial"),
        ("translations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_urgent_need_types, remove_urgent_need_types),
    ]
