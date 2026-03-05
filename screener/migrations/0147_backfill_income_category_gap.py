from django.db import migrations


def backfill_income_category_gap(apps, schema_editor):
    """
    Backfill the category field for IncomeStream records created after migration
    0126_add_income_category_with_backfill ran (December 2025) but before the
    frontend began persisting category on new submissions.

    Only rows where category IS NULL and type IS NOT NULL are affected.
    """
    IncomeStream = apps.get_model("screener", "IncomeStream")

    INCOME_TYPE_TO_CATEGORY = {
        # Employment
        "wages": "employment",
        "selfEmployment": "employment",
        # Government benefits
        "sSDisability": "government",
        "sSRetirement": "government",
        "sSI": "government",
        "sSSurvivor": "government",
        "sSDependent": "government",
        "unemployment": "government",
        "cashAssistance": "government",
        "cOSDisability": "government",
        "workersComp": "government",
        "veteran": "government",
        "stateDisability": "government",  # TX, MA
        "iLStateDisability": "government",  # IL
        # Support and gifts
        "childSupport": "support",
        "alimony": "support",
        "gifts": "support",
        "boarder": "support",
        # Investment and retirement
        "pension": "investment",
        "investment": "investment",
        "rental": "investment",
        "deferredComp": "investment",
    }

    streams = IncomeStream.objects.filter(category__isnull=True).exclude(type__isnull=True).exclude(type="")
    updated_count = 0
    for stream in streams:
        category = INCOME_TYPE_TO_CATEGORY.get(stream.type)
        if category:
            stream.category = category
            stream.save(update_fields=["category"])
            updated_count += 1

    print(f"Backfilled {updated_count} gap IncomeStream records with categories")


def reverse_backfill(apps, schema_editor):
    # Not reversible — we can't know which rows had category=None intentionally vs gap.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0146_merge_20260224_0000"),
    ]

    operations = [
        migrations.RunPython(backfill_income_category_gap, reverse_backfill),
    ]
