from django.db import migrations


# Seeds the two calculated labels added to citizenshipFilterConfig.tsx for programs that cover
# lawfully present pregnant people and children under 19 but not undocumented ones. They test the
# same conditions as `otherHealthCarePregnant` and `otherHealthCareUnder19`, but are linked only to
# `gc_5less`, `otherWithWorkPermission` and `refugee`. The old pair is also linked to `non_citizen`,
# which is right for CO Medicaid and wrong for NC Medicaid, where undocumented people get Emergency
# Medicaid only (MA-3330).
#
# This migration only creates the labels. Assigning them to programs is done in admin, so no
# program's `legal_status_required` is changed here.
#
# `get_or_create` is safe for these two names only: neither exists in any environment yet, and
# `LegalStatus.status` has no unique constraint, so the set is kept explicit rather than open-ended.
SEEDABLE = {"lawfulHealthCarePregnant", "lawfulHealthCareUnder19"}


def seed_statuses(apps, schema_editor):
    LegalStatus = apps.get_model("programs", "LegalStatus")

    for status in sorted(SEEDABLE):
        _, created = LegalStatus.objects.get_or_create(status=status)
        print(f"➕ seeded legal status '{status}'" if created else f"✔️  legal status '{status}' already exists")


def remove_statuses(apps, schema_editor):
    """
    Deleting a LegalStatus also drops it from every program it was assigned to in admin. That is
    the intended rollback: once the frontend no longer defines a label, an assignment to it never
    matches anyway.
    """
    LegalStatus = apps.get_model("programs", "LegalStatus")

    _, deleted = LegalStatus.objects.filter(status__in=SEEDABLE).delete()
    print(f"⏪ removed {deleted.get('programs.LegalStatus', 0)} legal status rows: {', '.join(sorted(SEEDABLE))}")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0204_move_national_navigator_copies_to_federal"),
    ]

    operations = [
        migrations.RunPython(seed_statuses, remove_statuses),
    ]
