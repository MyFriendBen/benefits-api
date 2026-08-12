# Generated manually to seed the "Type short" (UrgentNeedCategory) tags needed
# for MFB-1310: NC - Add two new urgent need types to NC white label:
#   Homeless Services & Free/Low-Cost Medical Care
#
# 0165 already created the two UrgentNeedType ("Type") rows used for admin
# categorization, but that field is separate from the one that actually drives
# results-page matching: screener/views.py's urgent_need_results() filters
# UrgentNeed.type_short__name against a fixed set of strings, and neither of
# the two new strings ("homeless services", "free low cost medical care")
# existed as UrgentNeedCategory rows anywhere in the system.
#
# UrgentNeedCategory has no white_label field (it's a shared, platform-wide
# list), so creating new rows through the admin is restricted to superusers.
# Seeding them here via migration avoids that bottleneck and guarantees the
# exact string values match what possible_needs expects -- no risk of a typo
# from someone hand-typing them into the admin.

from django.db import migrations

NEW_URGENT_NEED_CATEGORIES = [
    "homeless services",
    "free low cost medical care",
]


def add_urgent_need_categories(apps, schema_editor):
    UrgentNeedCategory = apps.get_model("programs", "UrgentNeedCategory")

    for name in NEW_URGENT_NEED_CATEGORIES:
        UrgentNeedCategory.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0165_add_nc_homeless_and_health_care_urgent_need_types"),
    ]

    operations = [
        # Reverse is a no-op, not a delete-by-name: UrgentNeedCategory has no field
        # that distinguishes a row created here from one that already existed or was
        # reused later (e.g. import_urgent_need_config.py's _set_categories also
        # get_or_create()s by this same name). Deleting by name on rollback would
        # silently strip type_short off any real UrgentNeed resource that had since
        # attached itself to one of these categories.
        migrations.RunPython(add_urgent_need_categories, migrations.RunPython.noop),
    ]