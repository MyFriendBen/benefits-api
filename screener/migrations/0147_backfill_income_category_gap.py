from django.db import migrations


def backfill_income_category_gap(apps, schema_editor):
    """
    Two-part fix for income stream category data:

    1. Gap window: Backfill category=NULL rows created after migration 0126 ran
       (December 2025) but before the frontend began persisting category.

    2. Category correction: Migration 0126 placed 'rental' and 'boarder' under
       'investment'. The config has since introduced a dedicated 'property'
       category for these types. Correct any rows set to 'investment' for these
       two types.
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
        "workersComp": "government",
        "veteran": "government",
        "cOSDisability": "government",  # CO
        "stateDisability": "government",  # TX, MA
        "iLStateDisability": "government",  # IL
        # Investment and retirement
        "pension": "investment",
        "investment": "investment",
        "deferredComp": "investment",
        # Property income (split out from 'investment' in 0126)
        "rental": "property",
        "boarder": "property",
        # Family support and gifts
        "childSupport": "support",
        "alimony": "support",
        "gifts": "support",
    }

    # Part 1: fill NULL category rows from the gap window
    from django.db.models import Case, Value, When

    gap_count = IncomeStream.objects.filter(
        category__isnull=True,
        type__in=list(INCOME_TYPE_TO_CATEGORY.keys()),
    ).update(
        category=Case(
            *[When(type=t, then=Value(c)) for t, c in INCOME_TYPE_TO_CATEGORY.items()],
        )
    )

    # Part 2: correct rental/boarder rows that 0126 set to 'investment'
    correction_count = IncomeStream.objects.filter(type__in=["rental", "boarder"], category="investment").update(
        category="property"
    )

    print(f"Backfilled {gap_count} gap rows; corrected {correction_count} rental/boarder rows to 'property'")


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
