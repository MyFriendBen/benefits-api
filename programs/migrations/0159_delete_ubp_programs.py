# Colorado Utility Bill Help / Utility Bill Pay ended 2026-05-31. Both calculators
# (co `ubp` and cesn `cesn_ubp`) were removed from the codebase, so the Program
# records are no longer needed. Deleting them removes UBP from results and the
# has-benefits step (HasBenefitsProgramsView filters the live Program table).
#
# The three FKs pointing to Program — CurrentBenefit.program, ProgramNavigator.program,
# and TranslationOverride.program — are all on_delete=CASCADE, so their rows are removed
# automatically; the delete is not blocked. ProgramEligibilitySnapshot references
# programs by CharField (name_abbreviated), not FK, so historical eligibility snapshots
# are intentionally preserved. Orphaned Translation rows are left in place, matching
# precedent 0139/0143 (PROTECT on Program->Translation does not block deleting Program).

from django.db import migrations


def delete_ubp_programs(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(white_label__code="co", name_abbreviated="ubp").delete()
    Program.objects.filter(white_label__code="cesn", name_abbreviated="cesn_ubp").delete()


def reverse(apps, schema_editor):
    # No-op: the ubp/cesn_ubp calculators no longer exist, so recreating these Program
    # rows would point at deleted calculators and crash the app. Re-adding a dead program
    # is not a real rollback need.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0158_program_program_name_abbreviated_lowercase"),
    ]

    operations = [
        migrations.RunPython(delete_ubp_programs, reverse),
    ]
