"""
Remove legal status rows whose label isn't in `LegalStatusLabel`, matching what 0211 does for
navigator languages.

Staging and prod hold only known labels (audited 2026-11-16), so this is a guard for databases
that picked one up from an old import. An unknown row no program or warning uses is deleted; one
that is still in use stops the migration with the programs and warnings it's on, rather than
being guessed at.
"""

from django.db import migrations

KNOWN = {
    "citizen", "non_citizen", "gc_5plus", "gc_5less", "refugee", "otherWithWorkPermission", "gc_18plus_no5",
    "gc_under18_no5", "otherHealthCareUnder19", "otherHealthCarePregnant", "notPregnantOrUnder19ForOmniSalud",
    "notPregnantOrUnder19ForEmergencyMedicaid", "notPregnantForMassHealthLimited",
    "notPregnantOrChildForMassHealthLimited", "otherHealthCareUnder21", "lawfulHealthCarePregnant",
    "lawfulHealthCareUnder19",
}


def remove_unknown(apps, schema_editor):
    LegalStatus = apps.get_model("programs", "LegalStatus")
    Program = apps.get_model("programs", "Program")
    WarningMessage = apps.get_model("programs", "WarningMessage")

    for status in LegalStatus.objects.exclude(status__in=KNOWN):
        users = [
            f"program {name}" for name in Program.objects.filter(legal_status_required=status).values_list(
                "name_abbreviated", flat=True
            )
        ] + [
            f"warning {name}" for name in WarningMessage.objects.filter(legal_statuses=status).values_list(
                "external_name", flat=True
            )
        ]
        if users:
            raise RuntimeError(
                f"Legal status '{status.status}' isn't known and is used by: {', '.join(sorted(map(str, users)))}. "
                f"Move them to a known label, or add it to the screener and LegalStatusLabel."
            )
        status.delete()


class Migration(migrations.Migration):
    dependencies = [("programs", "0212_legal_status_and_language_validators")]

    # A deleted row was unknown and unused, so reversing has nothing to restore.
    operations = [migrations.RunPython(remove_unknown, migrations.RunPython.noop)]
