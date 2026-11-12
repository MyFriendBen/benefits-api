# Generated manually to seed the "Type short" (UrgentNeedCategory) tag needed for
# the new "Help with drug or alcohol use" NC urgent need category, and to move the
# existing "Alcohol Drug Council of NC" resource onto it.
#
# 0209 already created the UrgentNeedType ("Type") row used for admin categorization,
# but that field is separate from the one that actually drives results-page matching:
# resource selection filters UrgentNeed.type_short__name against NEED_CATEGORY_FIELDS
# (screener/urgent_needs.py), and "drug alcohol use" didn't exist as an UrgentNeedCategory
# row anywhere in the system.
#
# UrgentNeedCategory has no white_label field (it's a shared, platform-wide list), so
# creating new rows through the admin is restricted to superusers. Seeding it here via
# migration avoids that bottleneck and guarantees the exact string value matches what
# NEED_CATEGORY_FIELDS expects.
#
# "Alcohol Drug Council of NC" (external_name="nc_alcohol_drug_council_of_north_carolina")
# currently sits under the generic "mental health" / Behavioral health category. Moving
# it here was the whole point of adding this category, so it's folded into the same
# migration rather than left as a manual admin edit.

from django.db import migrations

NC_WHITE_LABEL_CODE = "nc"
NEW_URGENT_NEED_CATEGORIES = [
    "drug alcohol use",
]
ALCOHOL_DRUG_COUNCIL_EXTERNAL_NAME = "nc_alcohol_drug_council_of_north_carolina"
NEW_URGENT_NEED_TYPE_EXTERNAL_NAME = "nc_drug_alcohol_use"


def add_urgent_need_categories(apps, schema_editor):
    UrgentNeedCategory = apps.get_model("programs", "UrgentNeedCategory")
    UrgentNeedType = apps.get_model("programs", "UrgentNeedType")
    UrgentNeed = apps.get_model("programs", "UrgentNeed")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    drug_alcohol_use_category, _ = UrgentNeedCategory.objects.get_or_create(name=NEW_URGENT_NEED_CATEGORIES[0])

    white_label = WhiteLabel.objects.filter(code=NC_WHITE_LABEL_CODE).first()
    if white_label is None:
        # NC white label not present in this environment (e.g. some test DBs); skip
        # the resource reassignment below, there's nothing to reassign.
        return

    drug_alcohol_use_type = UrgentNeedType.objects.filter(
        white_label=white_label, external_name=NEW_URGENT_NEED_TYPE_EXTERNAL_NAME
    ).first()
    if drug_alcohol_use_type is None:
        return

    alcohol_drug_council = UrgentNeed.objects.filter(external_name=ALCOHOL_DRUG_COUNCIL_EXTERNAL_NAME).first()
    if alcohol_drug_council is None:
        # Resource not present in this environment; nothing to reassign.
        return

    UrgentNeed.objects.filter(pk=alcohol_drug_council.pk).update(
        category_type_id=drug_alcohol_use_type.pk
    )
    alcohol_drug_council.type_short.set([drug_alcohol_use_category])


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0209_add_nc_drug_alcohol_use_urgent_need_type"),
    ]

    operations = [
        # Reverse is a no-op, not a delete-by-name/unassign: UrgentNeedCategory has no
        # field that distinguishes a row created here from one that already existed or
        # was reused later (e.g. import_urgent_need_config.py's _set_categories also
        # get_or_create()s by this same name). Deleting by name, or reverting the
        # resource's category assignment, on rollback would silently affect editorial
        # content a human may have further edited since this migration ran.
        migrations.RunPython(add_urgent_need_categories, migrations.RunPython.noop),
    ]
