# Generated migration to replace legacy 'other' value with 'otherWithWorkPermission'
from django.db import migrations


def migrate_other_to_other_with_work_permission(apps, schema_editor):
    """
    Replace 'other' in legal_status_required with 'otherWithWorkPermission'.

    Background: The frontend now uses the more specific 'otherWithWorkPermission'
    to clearly indicate lawfully present noncitizens with authorization.
    """
    Program = apps.get_model("programs", "Program")

    programs_updated = 0

    for program in Program.objects.all():
        legal_statuses = list(program.legal_status_required)

        if "other" in legal_statuses:
            # Replace 'other' with 'otherWithWorkPermission'
            legal_statuses.remove("other")

            if "otherWithWorkPermission" not in legal_statuses:
                legal_statuses.append("otherWithWorkPermission")

            program.legal_status_required = legal_statuses
            program.save(update_fields=["legal_status_required"])
            programs_updated += 1

    print(f"✅ Migrated {programs_updated} programs: 'other' → 'otherWithWorkPermission'")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration: Replace 'otherWithWorkPermission' back with 'other'.
    """
    Program = apps.get_model("programs", "Program")

    programs_updated = 0

    for program in Program.objects.all():
        legal_statuses = list(program.legal_status_required)

        if "otherWithWorkPermission" in legal_statuses:
            legal_statuses.remove("otherWithWorkPermission")

            if "other" not in legal_statuses:
                legal_statuses.append("other")

            program.legal_status_required = legal_statuses
            program.save(update_fields=["legal_status_required"])
            programs_updated += 1

    print(f"⏪ Reversed {programs_updated} programs: 'otherWithWorkPermission' → 'other'")


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0127_migrate_green_card_legal_status"),
    ]

    operations = [
        migrations.RunPython(migrate_other_to_other_with_work_permission, reverse_migration),
    ]
