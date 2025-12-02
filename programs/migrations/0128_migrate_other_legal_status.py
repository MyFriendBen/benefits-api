# Generated migration to remove legacy 'other' value (people without work permission)
from django.db import migrations


def remove_other_status(apps, schema_editor):
    """
    Remove 'other' from legal_status_required.

    Background: The 'other' status represented people without work permission,
    which is not a valid eligibility category. Programs should not use this status.
    """
    Program = apps.get_model("programs", "Program")
    LegalStatus = apps.get_model("programs", "LegalStatus")

    programs_updated = 0

    try:
        other = LegalStatus.objects.get(status="other")
    except LegalStatus.DoesNotExist:
        print("⚠️  'other' status not found - skipping migration")
        return

    for program in Program.objects.all():
        current_statuses = program.legal_status_required.all()
        status_names = [s.status for s in current_statuses]

        if "other" in status_names:
            # Remove 'other' without replacement (it was for people without work permission)
            program.legal_status_required.remove(other)
            programs_updated += 1

    print(f"✅ Removed 'other' status from {programs_updated} programs (represented people without work permission)")


def reverse_migration(_apps, _schema_editor):
    """
    Reverse migration: Add back 'other' status to programs.
    """
    # This is a safe no-op reverse - we can't know which programs should get 'other' back
    # since it represented people without work permission (not a valid eligibility category)
    print("⏪ Reverse migration: 'other' status not restored (represented invalid eligibility)")


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0127_migrate_green_card_legal_status"),
    ]

    operations = [
        migrations.RunPython(remove_other_status, reverse_migration),
    ]
