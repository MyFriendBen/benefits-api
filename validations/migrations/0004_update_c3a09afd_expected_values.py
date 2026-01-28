# Data migration to update expected values for screen c3a09afd
# after adding UnemploymentIncomeDependency to irs_gross_income
#
# MFB-617: https://github.com/your-org/benefits-api/issues/617
#
# Screen c3a09afd household:
#   - 5 members: Head (36), Spouse (34), 3 children (15, 11, 7)
#   - Wages: $4,200/month = $50,400/year
#   - Unemployment: $200/month = $2,400/year
#   - Total income: $52,800/year
#
# Per 26 U.S. Code Section 85, unemployment compensation is included in gross income.
# This increases AGI, which affects the EITC phase-out calculation:
#   - EITC phase-out uses max(earned_income, AGI)
#   - Unemployment doesn't count as earned income (phase-in)
#   - But unemployment DOES count toward AGI (phase-out)
#   - Higher AGI = more phase-out reduction = lower EITC
#
from decimal import Decimal
from django.db import migrations

SCREEN_UUID = "c3a09afd-8e0a-4e3a-9d26-df3c46809302"

# New expected values calculated with unemployment income included in irs_gross_income.
#
# Calculation notes:
#   - Federal EITC: With 3 children and $50,400 earned income + $2,400 unemployment,
#     AGI of $52,800 triggers significant phase-out reduction. Result: $2,952
#   - IL EITC: 20% of federal EITC = $2,952 * 0.20 = $590.40, rounded to $590
#   - IL CTC: 20% of IL EITC for eligible children under 12 = $590 * 0.20 = $118
#
UPDATED_VALUES = {
    "il_federal_eitc": {
        "eligible": True,
        "value": Decimal("2952.00"),
        "notes": "MFB-617: Updated for unemployment in AGI. 3 children, $52,800 AGI triggers phase-out.",
    },
    "il_eitc": {
        "eligible": True,
        "value": Decimal("590.00"),
        "notes": "MFB-617: 20% of federal EITC ($2,952). Reduced due to unemployment in AGI.",
    },
    "il_ctc": {
        "eligible": True,
        "value": Decimal("118.00"),
        "notes": "MFB-617: 20% of IL EITC ($590). 2 children under 12 qualify.",
    },
}


def update_validation_expected_values(apps, schema_editor):
    """
    Update expected values for validation screen c3a09afd.

    This screen has unemployment income ($200/month), which now affects
    irs_gross_income calculations. The EITC values are reduced because
    unemployment increases AGI for phase-out purposes.

    Note: This migration gracefully skips if the screen or validations don't exist,
    which is expected in local/staging environments where production data isn't present.
    """
    Validation = apps.get_model("validations", "Validation")
    Screen = apps.get_model("screener", "Screen")

    try:
        screen = Screen.objects.get(uuid=SCREEN_UUID)
    except Screen.DoesNotExist:
        # Expected in local/staging - screen only exists in production
        print(f"  [SKIP] Screen {SCREEN_UUID} not found (expected in local/staging)")
        return

    updated_count = 0
    for program_name, new_values in UPDATED_VALUES.items():
        try:
            validation = Validation.objects.get(screen=screen, program_name=program_name)
            old_value = validation.value
            validation.eligible = new_values["eligible"]
            validation.value = new_values["value"]
            validation.notes = new_values.get("notes", "")
            validation.save()
            updated_count += 1
            print(f"  Updated {program_name}: ${old_value} -> ${new_values['value']}")
        except Validation.DoesNotExist:
            print(f"  [SKIP] Validation for {program_name} not found")

    if updated_count > 0:
        print(f"  Updated {updated_count} validation expected values for screen {SCREEN_UUID}")
    else:
        print(f"  [SKIP] No validations updated for screen {SCREEN_UUID}")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration: restore original expected values.

    Note: This migration gracefully skips if the screen or validations don't exist,
    which is expected in local/staging environments where production data isn't present.
    """
    Validation = apps.get_model("validations", "Validation")
    Screen = apps.get_model("screener", "Screen")

    # Original values (before unemployment was included in irs_gross_income)
    original_values = {
        "il_federal_eitc": {"eligible": True, "value": Decimal("3848.00")},
        "il_eitc": {"eligible": True, "value": Decimal("769.00")},
        "il_ctc": {"eligible": True, "value": Decimal("307.00")},
    }

    try:
        screen = Screen.objects.get(uuid=SCREEN_UUID)
    except Screen.DoesNotExist:
        # Expected in local/staging - screen only exists in production
        print(f"  [SKIP] Screen {SCREEN_UUID} not found (expected in local/staging)")
        return

    updated_count = 0
    for program_name, old_values in original_values.items():
        try:
            validation = Validation.objects.get(screen=screen, program_name=program_name)
            validation.eligible = old_values["eligible"]
            validation.value = old_values["value"]
            validation.save()
            updated_count += 1
        except Validation.DoesNotExist:
            pass

    if updated_count > 0:
        print(f"  Restored {updated_count} validation expected values for screen {SCREEN_UUID}")
    else:
        print(f"  [SKIP] No validations restored for screen {SCREEN_UUID}")


class Migration(migrations.Migration):

    dependencies = [
        ("validations", "0003_validation_notes"),
        ("screener", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(update_validation_expected_values, reverse_migration),
    ]
