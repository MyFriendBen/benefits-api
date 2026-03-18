from django.db import migrations
from django.db.models import Case, Value, When

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
    "workersComp": "government",
    "veteran": "government",
    "cOSDisability": "government",
    "stateDisability": "government",
    "iLStateDisability": "government",
    # Investment and retirement
    "pension": "investment",
    "investment": "investment",
    "deferredComp": "investment",
    # Property income
    "rental": "property",
    "boarder": "property",
    # Family support and gifts
    "childSupport": "support",
    "alimony": "support",
    "gifts": "support",
}


def fix_income_category_backfill(apps, schema_editor):
    """
    Migration 0147 crashed mid-loop due to concurrent row deletions while
    iterating 24k+ rows with individual .save() calls. This migration
    completes the backfill for any rows that were missed, using bulk update.
    """
    IncomeStream = apps.get_model("screener", "IncomeStream")

    # Complete Part 1: fill any remaining NULL category rows
    gap_count = IncomeStream.objects.filter(
        category__isnull=True,
        type__in=list(INCOME_TYPE_TO_CATEGORY.keys()),
    ).update(
        category=Case(
            *[When(type=t, then=Value(c)) for t, c in INCOME_TYPE_TO_CATEGORY.items()],
        )
    )

    # Re-run Part 2 in case it was also skipped (it's idempotent)
    correction_count = IncomeStream.objects.filter(type__in=["rental", "boarder"], category="investment").update(
        category="property"
    )

    print(f"Fixed {gap_count} remaining gap rows; corrected {correction_count} rental/boarder rows to 'property'")


def reverse_fix(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0147_backfill_income_category_gap"),
    ]

    operations = [
        migrations.RunPython(fix_income_category_backfill, reverse_fix),
    ]
