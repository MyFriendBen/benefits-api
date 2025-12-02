# Generated migration to update LegalStatus table options
from django.db import migrations


def update_legal_status_options(apps, schema_editor):
    """
    Remove legacy 'green_card' and 'other' legal status options.
    Ensure current legal status options exist: 'gc_5plus', 'gc_5less', etc.

    Note: 'other' represented people without work permission - not a valid eligibility category.
    """
    LegalStatus = apps.get_model("programs", "LegalStatus")

    # Remove legacy options
    deleted_green_card = LegalStatus.objects.filter(status="green_card").delete()
    deleted_other = LegalStatus.objects.filter(status="other").delete()

    print(f"🗑️  Removed legacy LegalStatus options:")
    print(f"   - green_card: {deleted_green_card[0]} rows (replaced by gc_5plus/gc_5less)")
    print(f"   - other: {deleted_other[0]} rows (people without work permission - invalid)")

    # Ensure all current legal status options exist
    current_statuses = ["gc_5plus", "gc_5less", "otherWithWorkPermission", "citizen", "non_citizen", "refugee"]
    created_count = 0

    for status_name in current_statuses:
        _, created = LegalStatus.objects.get_or_create(status=status_name)
        if created:
            created_count += 1

    print(f"✅ Ensured {len(current_statuses)} legal status options exist ({created_count} newly created)")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration: Add back 'green_card' and 'other', remove new subtypes.
    """
    LegalStatus = apps.get_model("programs", "LegalStatus")

    # Add back legacy options
    LegalStatus.objects.get_or_create(status="green_card")
    LegalStatus.objects.get_or_create(status="other")

    # Optionally remove the new subtypes (commented out to be safe)
    # LegalStatus.objects.filter(status='gc_5plus').delete()
    # LegalStatus.objects.filter(status='gc_5less').delete()
    # LegalStatus.objects.filter(status='otherWithWorkPermission').delete()

    print("⏪ Restored legacy legal status options: 'green_card', 'other'")


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0128_remove_other_legal_status"),
    ]

    operations = [
        migrations.RunPython(update_legal_status_options, reverse_migration),
    ]
