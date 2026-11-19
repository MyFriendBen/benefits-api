"""
The values benefits-api accepts for the screener's enumerated household answers: relationships,
income and expense types, and frequencies.

The white label configs (`configuration/white_labels/`) are the one definition of what the
screener offers. `add_config` serves them to the screener, and the sets here are built from the
same modules, so a value is accepted wherever any white label offers it. The union, not each
screen's own white label, because the Get Ahead apps post `co_tax_calculator` screens and test
screens use `federal`, and neither has a config module.

Some accepted values are set by code rather than offered as a choice: the first member is always
`headOfHousehold`, and the energy calculator sends its own expense types.

`request_language_code` isn't checked: an unknown code already falls back to English, and a code
from an older config (`zh`, now `zh-hans`) can sit in a returning user's browser and arrive on a new
screen, which refusing would stop at the first step.

A screen being edited keeps any value it already holds. Answers that were valid when they were
given (options since retired, like the `auto` and `creditCard` expenses) stay on tens of thousands
of saved screens, and the screener sends them back when someone reopens one. Rejecting them would
break that screen without fixing anything.
"""

from collections.abc import Iterable, Mapping
from typing import Any

# `acute_condition_options` config key -> the `Screen` field the answer is saved to. The one
# definition: the screen API takes and returns needs as these keys (`acute_needs`), and Benji reads
# it too. A white label can only offer a need listed here: `configuration/test_served_lists.py`
# checks every config.
ACUTE_OPTION_FIELDS: dict[str, str] = {
    "food": "needs_food",
    "babySupplies": "needs_baby_supplies",
    "housing": "needs_housing_help",
    "support": "needs_mental_health_help",
    "childDevelopment": "needs_child_dev_help",
    "familyPlanning": "needs_family_planning_help",
    "jobResources": "needs_job_resources",
    "dentalCare": "needs_dental_care",
    "legalServices": "needs_legal_services",
    "savings": "needs_college_savings",
    "veteranServices": "needs_veteran_services",
    "disabilityResources": "needs_disability_resources",
    "agingResources": "needs_aging_resources",
    "homelessServices": "needs_homeless_services",
    "freeLowCostMedicalCare": "needs_free_low_cost_medical_care",
    "transportation": "needs_transportation",
    "medicalExpensesAndDebt": "needs_medical_expenses_and_debt",
    "drugAlcoholUse": "needs_drug_alcohol_use",
}

# Set by the screener for the first member, never offered as a choice. Calculators read it.
HEAD_OF_HOUSEHOLD_RELATIONSHIP = "headOfHousehold"


def needs_fields(selected: Iterable[str] | None) -> dict[str, bool]:
    """The `needs_*` column values for the selected needs: each listed one set, the rest cleared.
    None leaves the columns alone."""
    if selected is None:
        return {}
    chosen = set(selected)
    return {field: key in chosen for key, field in ACUTE_OPTION_FIELDS.items()}


def needs_selected(screen: Any) -> list[str]:
    """The needs a saved screen has, as option keys."""
    return [key for key, field in ACUTE_OPTION_FIELDS.items() if getattr(screen, field)]


def _nested_keys(options_by_category: Mapping[str, Mapping[str, Any]]) -> set[str]:
    return {key for options in options_by_category.values() for key in options}


def accepted_values() -> dict[str, frozenset[str]]:
    """Every value each answer may take, across all white labels."""
    from configuration.white_labels import white_label_config
    from screener.models import Expense

    relationships: set[str] = {HEAD_OF_HOUSEHOLD_RELATIONSHIP}
    income_categories: set[str] = set()
    income_types: set[str] = set()
    frequencies: set[str] = set()
    expense_types: set[str] = set()
    for config in white_label_config.values():
        relationships |= set(config.relationship_options)
        income_categories |= set(config.income_categories)
        income_types |= _nested_keys(config.income_options_by_category)
        frequencies |= set(config.frequency_options)
        expense_types |= _nested_keys(config.expense_options_by_category)
        expense_types |= set(config.energy_calculator_expense_options)

    return {
        "relationship": frozenset(relationships),
        "income_category": frozenset(income_categories),
        "income_type": frozenset(income_types),
        "income_frequency": frozenset(frequencies),
        "expense_type": frozenset(expense_types),
        # `Expense.monthly()` has no hourly branch, so an hourly expense can't be used.
        "expense_frequency": frozenset(frequencies & Expense.SUPPORTED_FREQUENCIES),
    }


def _held_values(screen: Any) -> dict[str, set[str]]:
    """The values a saved screen already holds, which an edit may send back unchanged."""
    if screen is None:
        return {}

    members = list(screen.household_members.all())
    incomes = list(screen.income_streams.all())
    expenses = list(screen.expenses.all())
    return {
        "relationship": {m.relationship for m in members},
        "income_category": {i.category for i in incomes},
        "income_type": {i.type for i in incomes},
        "income_frequency": {i.frequency for i in incomes},
        "expense_type": {e.type for e in expenses},
        "expense_frequency": {e.frequency for e in expenses},
    }


def _submitted(attrs: Mapping[str, Any]) -> Iterable[tuple[str, str, str]]:
    """(answer, payload path, value) for every enumerated answer in a screen payload."""
    for m, member in enumerate(attrs.get("household_members") or []):
        yield "relationship", f"household_members[{m}].relationship", member.get("relationship")
        for i, income in enumerate(member.get("income_streams") or []):
            path = f"household_members[{m}].income_streams[{i}]"
            yield "income_category", f"{path}.category", income.get("category")
            yield "income_type", f"{path}.type", income.get("type")
            yield "income_frequency", f"{path}.frequency", income.get("frequency")

    for e, expense in enumerate(attrs.get("expenses") or []):
        yield "expense_type", f"expenses[{e}].type", expense.get("type")
        yield "expense_frequency", f"expenses[{e}].frequency", expense.get("frequency")


def unaccepted_values(attrs: Mapping[str, Any], screen: Any = None) -> dict[str, str]:
    """
    Error messages, by payload path, for each answer outside the accepted values.

    A blank answer is left to the calculators, which already treat it as missing. `screen` is the
    saved screen when the payload edits one; any value it already holds is accepted.
    """
    accepted = accepted_values()
    unknown = [
        (answer, path, value)
        for answer, path, value in _submitted(attrs)
        if value not in (None, "") and value not in accepted[answer]
    ]
    if not unknown:
        return {}

    held = _held_values(screen)
    errors: dict[str, str] = {}
    for answer, path, value in unknown:
        if value in held.get(answer, set()):
            continue
        errors[path] = (
            f"'{value}' isn't a {answer.replace('_', ' ')} the screener offers. "
            f"Use one of {', '.join(sorted(accepted[answer]))}."
        )
    return errors
