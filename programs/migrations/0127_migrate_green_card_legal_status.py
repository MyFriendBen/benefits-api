# Generated migration to replace legacy 'green_card' value with 'gc_5plus' and 'gc_5less'
from django.db import migrations


def migrate_green_card_to_subtypes(apps, schema_editor):
    """
    Replace 'green_card' in legal_status_required with both 'gc_5plus' and 'gc_5less'.

    Background: The frontend never allowed selecting just 'green_card' - users always
    had to choose a subtype. This migration ensures program data matches frontend behavior.
    """
    Program = apps.get_model("programs", "Program")
    LegalStatus = apps.get_model("programs", "LegalStatus")

    programs_updated = 0

    # Get LegalStatus objects for lookup
    try:
        green_card = LegalStatus.objects.get(status="green_card")
    except LegalStatus.DoesNotExist:
        print("⚠️  'green_card' status not found - skipping migration")
        return

    gc_5plus, _ = LegalStatus.objects.get_or_create(status="gc_5plus")
    gc_5less, _ = LegalStatus.objects.get_or_create(status="gc_5less")

    for program in Program.objects.all():
        current_statuses = program.legal_status_required.all()
        status_names = [s.status for s in current_statuses]

        if "green_card" in status_names:
            # Remove the legacy 'green_card' value
            program.legal_status_required.remove(green_card)

            # Only add both subtypes if NEITHER is already present
            # If one subtype is already specified, keep just that one
            has_gc_5plus = "gc_5plus" in status_names
            has_gc_5less = "gc_5less" in status_names

            if not has_gc_5plus and not has_gc_5less:
                # Neither subtype present, add both
                program.legal_status_required.add(gc_5plus)
                program.legal_status_required.add(gc_5less)
            # If one or both subtypes already present, leave them as-is

            programs_updated += 1

    print(f"✅ Migrated {programs_updated} programs: 'green_card' → ['gc_5plus', 'gc_5less']")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration: Cannot reliably reverse without knowing original state.

    The forward migration removes 'green_card' and conditionally adds subtypes.
    We can't determine which subtypes were added by migration vs. already present.

    Possible original states:
    - green_card only → adds both subtypes
    - green_card + gc_5plus → keeps gc_5plus only
    - green_card + gc_5less → keeps gc_5less only
    - green_card + both → keeps both

    Safe no-op: Re-add 'green_card' option to LegalStatus table for manual cleanup.
    Admins should manually review programs and adjust as needed.
    """
    LegalStatus = apps.get_model("programs", "LegalStatus")

    # Just restore the green_card option to the LegalStatus table
    LegalStatus.objects.get_or_create(status="green_card")

    print("⚠️  Reverse migration: 'green_card' restored to LegalStatus table.")
    print("⚠️  Programs not automatically reverted - manual review required.")
    print("⚠️  Cannot determine original subtype configuration without data loss.")


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0126_add_navigator_ordering"),
    ]

    operations = [
        migrations.RunPython(migrate_green_card_to_subtypes, reverse_migration),
    ]
