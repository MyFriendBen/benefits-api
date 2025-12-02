# Generated migration to replace legacy 'green_card' value with 'gc_5plus' and 'gc_5less'
from django.db import migrations


def migrate_green_card_to_subtypes(apps, schema_editor):
    """
    Replace 'green_card' in legal_status_required with both 'gc_5plus' and 'gc_5less'.

    Background: The frontend never allowed selecting just 'green_card' - users always
    had to choose a subtype. This migration ensures program data matches frontend behavior.
    """
    Program = apps.get_model("programs", "Program")

    programs_updated = 0

    for program in Program.objects.all():
        legal_statuses = list(program.legal_status_required)

        if "green_card" in legal_statuses:
            # Remove the legacy 'green_card' value
            legal_statuses.remove("green_card")

            # Add both subtypes if not already present
            if "gc_5plus" not in legal_statuses:
                legal_statuses.append("gc_5plus")
            if "gc_5less" not in legal_statuses:
                legal_statuses.append("gc_5less")

            program.legal_status_required = legal_statuses
            program.save(update_fields=["legal_status_required"])
            programs_updated += 1

    print(f"✅ Migrated {programs_updated} programs: 'green_card' → ['gc_5plus', 'gc_5less']")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration: Replace 'gc_5plus' AND 'gc_5less' back with 'green_card'.
    Only replaces if BOTH are present.
    """
    Program = apps.get_model("programs", "Program")

    programs_updated = 0

    for program in Program.objects.all():
        legal_statuses = list(program.legal_status_required)

        # Only reverse if both subtypes are present
        if "gc_5plus" in legal_statuses and "gc_5less" in legal_statuses:
            legal_statuses.remove("gc_5plus")
            legal_statuses.remove("gc_5less")

            if "green_card" not in legal_statuses:
                legal_statuses.append("green_card")

            program.legal_status_required = legal_statuses
            program.save(update_fields=["legal_status_required"])
            programs_updated += 1

    print(f"⏪ Reversed {programs_updated} programs: ['gc_5plus', 'gc_5less'] → 'green_card'")


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0126_add_navigator_ordering"),
    ]

    operations = [
        migrations.RunPython(migrate_green_card_to_subtypes, reverse_migration),
    ]
