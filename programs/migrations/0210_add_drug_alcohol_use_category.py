# MFB-2363: seeds the "drug alcohol use" UrgentNeedCategory ("Type short") and moves
# the existing NC "Alcohol Drug Council of North Carolina" resource onto the new
# category.
#
# 0209 created the shared UrgentNeedType (the heading shown on the resource card), but
# results-page matching is driven by a separate field: resource selection filters
# UrgentNeed.type_short__name against NEED_CATEGORY_FIELDS (screener/urgent_needs.py),
# and "drug alcohol use" didn't exist as an UrgentNeedCategory row.
#
# UrgentNeedCategory has no white_label field (it's a shared, platform-wide list), so
# only superusers can create rows in the admin. Seeding it here avoids that bottleneck
# and guarantees the exact string matches NEED_CATEGORY_FIELDS.
#
# The resource is fully swapped: its heading becomes the new type, and its Type short
# tags are replaced, so it no longer appears for "mental health". Confirmed as intended
# on MFB-2363. external_name is globally unique, so no white label is needed to find it.

from django.db import migrations

NEW_URGENT_NEED_CATEGORY = "drug alcohol use"
ALCOHOL_DRUG_COUNCIL_EXTERNAL_NAME = "nc_alcohol_drug_council_of_north_carolina"
NEW_URGENT_NEED_TYPE_EXTERNAL_NAME = "drug_alcohol_use"


def add_urgent_need_categories(apps, schema_editor):
    UrgentNeedCategory = apps.get_model("programs", "UrgentNeedCategory")
    UrgentNeedType = apps.get_model("programs", "UrgentNeedType")
    UrgentNeed = apps.get_model("programs", "UrgentNeed")

    drug_alcohol_use_category, _ = UrgentNeedCategory.objects.get_or_create(name=NEW_URGENT_NEED_CATEGORY)

    drug_alcohol_use_type = UrgentNeedType.objects.filter(external_name=NEW_URGENT_NEED_TYPE_EXTERNAL_NAME).first()
    if drug_alcohol_use_type is None:
        return

    alcohol_drug_council = UrgentNeed.objects.filter(external_name=ALCOHOL_DRUG_COUNCIL_EXTERNAL_NAME).first()
    if alcohol_drug_council is None:
        # Resource not present in this environment; nothing to reassign.
        return

    UrgentNeed.objects.filter(pk=alcohol_drug_council.pk).update(category_type_id=drug_alcohol_use_type.pk)
    alcohol_drug_council.type_short.set([drug_alcohol_use_category])


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0209_add_drug_alcohol_use_urgent_need_type"),
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
