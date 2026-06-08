# Cleans up NC ProgramCategory naming inconsistencies:
#
#   1. Deduplicates the two 'Cash Assistance' rows:
#        'nc cash'  (space)      — has SSI / SSDI / TANF programs pointing to it
#        'nc_cash'  (underscore) — orphan row, no programs
#      Repoints all programs to the underscore variant (canonical, matches
#      nc_housing convention) and deletes the space variant.
#
#   2. Renames remaining space-variant categories to use underscores:
#        'nc childcare'  → 'nc_childcare'
#        'nc food'       → 'nc_food'
#        'nc healthcare' → 'nc_healthcare'
#
# Not reversible — the deleted 'nc cash' Translation rows cannot be safely
# recreated automatically. Use a DB snapshot if a rollback is needed.
# Idempotent: skips steps where the deprecated rows are already gone.

from django.db import migrations


def deduplicate_nc_categories(apps, schema_editor):
    ProgramCategory = apps.get_model("programs", "ProgramCategory")
    Program = apps.get_model("programs", "Program")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    try:
        wl = WhiteLabel.objects.get(code="nc")
    except WhiteLabel.DoesNotExist:
        return  # NC tenant not present (safe for test environments)

    # 1. Deduplicate 'nc cash' (space) → 'nc_cash' (underscore)
    old_cash = ProgramCategory.objects.filter(white_label=wl, external_name="nc cash").first()
    canonical_cash = ProgramCategory.objects.filter(white_label=wl, external_name="nc_cash").first()

    if old_cash and canonical_cash:
        # Both exist (production scenario): migrate programs and delete old
        Program.objects.filter(category=old_cash).update(category=canonical_cash)
        old_cash.delete()

    elif old_cash and not canonical_cash:
        # Only old exists (local testing scenario): just rename it directly
        ProgramCategory.objects.filter(pk=old_cash.pk).update(external_name="nc_cash")

    # 2. Rename remaining space-variant categories to underscore form
    renames = [
        ("nc childcare", "nc_childcare"),
        ("nc food", "nc_food"),
        ("nc healthcare", "nc_healthcare"),
    ]
    for old_name, new_name in renames:
        ProgramCategory.objects.filter(white_label=wl, external_name=old_name).update(external_name=new_name)


def reverse_deduplicate_nc_categories(apps, schema_editor):
    raise NotImplementedError(
        "This migration is not reversible because 'nc cash' was deleted. " "Restore from a DB snapshot if needed."
    )


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0156_deactivate_co_my_spark"),
        ("screener", "0153_add_needs_disability_resources"),
    ]

    operations = [
        migrations.RunPython(
            deduplicate_nc_categories,
            reverse_deduplicate_nc_categories,
        ),
    ]
