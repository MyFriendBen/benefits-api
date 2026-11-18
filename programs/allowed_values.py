"""
The values benefits-api accepts for strings the screener interprets. Each list here is the one
authoritative source on the API side: every write path and the tests check against it, and adding
a value is adding it here (no migration). The check lives in code, not in a database constraint,
so a bulk `.update()` or raw SQL can bypass it; nothing writes these tables that way.

`add_config` serves the screener what it shows for each value: the six legal statuses a household
picks (`legal_status_options`, in button order) and the navigator language badges
(`navigator_language_options`). Navigator languages are the site's locales plus `ALL`, and a
test keeps them so.

The screener still holds logic per legal status: `CitizenLabels` in
benefits-calculator/src/Components/Results/Filter/citizenshipFilterConfig.tsx works out the
calculated statuses and which choices they follow. So a legal status takes a change in both repos,
and a test on each side pins the two lists together (`ScreenerParityTests` in
programs/test_allowed_values.py here, and src/Components/Results/apiAllowedValues.test.ts there).

Warning calculators aren't listed here: the registry in `programs.warnings` is their list.
"""

from django.core.exceptions import ValidationError
from django.db import models


class LegalStatusLabel(models.TextChoices):
    """
    Immigration-status labels a program's `legal_status_required` can hold.

    The results page shows a program only when the household's status is in its list, so a label
    the screener doesn't know matches nobody.
    """

    # Chosen by the household on the results page.
    CITIZEN = "citizen", "U.S. citizen"
    NON_CITIZEN = "non_citizen", "Undocumented"
    GC_5PLUS = "gc_5plus", "Green card, 5+ years"
    GC_5LESS = "gc_5less", "Green card, under 5 years"
    REFUGEE = "refugee", "Refugee or asylee"
    OTHER_WITH_WORK_PERMISSION = "otherWithWorkPermission", "Other lawful, with work permission"
    # Worked out by the screener from the household's members.
    GC_18PLUS_NO5 = "gc_18plus_no5", "Green card under 5 years, 18 or older"
    GC_UNDER18_NO5 = "gc_under18_no5", "Green card under 5 years, under 18"
    OTHER_HEALTH_CARE_UNDER19 = "otherHealthCareUnder19", "Other lawful, health care, under 19"
    OTHER_HEALTH_CARE_PREGNANT = "otherHealthCarePregnant", "Other lawful, health care, pregnant"
    NOT_PREGNANT_OR_UNDER19_FOR_OMNISALUD = "notPregnantOrUnder19ForOmniSalud", "OmniSalud: not pregnant or under 19"
    NOT_PREGNANT_OR_UNDER19_FOR_EMERGENCY_MEDICAID = (
        "notPregnantOrUnder19ForEmergencyMedicaid",
        "Emergency Medicaid: not pregnant or under 19",
    )
    NOT_PREGNANT_FOR_MASSHEALTH_LIMITED = "notPregnantForMassHealthLimited", "MassHealth Limited: not pregnant"
    NOT_PREGNANT_OR_CHILD_FOR_MASSHEALTH_LIMITED = (
        "notPregnantOrChildForMassHealthLimited",
        "MassHealth Limited: not pregnant or a child",
    )
    OTHER_HEALTH_CARE_UNDER21 = "otherHealthCareUnder21", "Other lawful, health care, under 21"
    LAWFUL_HEALTH_CARE_PREGNANT = "lawfulHealthCarePregnant", "Lawfully present, health care, pregnant"
    LAWFUL_HEALTH_CARE_UNDER19 = "lawfulHealthCareUnder19", "Lawfully present, health care, under 19"


USER_SELECTED_LEGAL_STATUSES = frozenset(
    {
        LegalStatusLabel.CITIZEN,
        LegalStatusLabel.NON_CITIZEN,
        LegalStatusLabel.GC_5PLUS,
        LegalStatusLabel.GC_5LESS,
        LegalStatusLabel.REFUGEE,
        LegalStatusLabel.OTHER_WITH_WORK_PERMISSION,
    }
)


class NavigatorLanguageCode(models.TextChoices):
    """
    Languages a navigator can list: every site locale (`settings.LANGUAGES`) plus `ALL`, for a
    navigator who serves any language. The program page draws a badge for each, and hides any other
    code. Each label is the spoken language's English name, which the badge and the assistant use.
    """

    ENGLISH = "en-us", "English"
    SPANISH = "es", "Spanish"
    VIETNAMESE = "vi", "Vietnamese"
    FRENCH = "fr", "French"
    AMHARIC = "am", "Amharic"
    SOMALI = "so", "Somali"
    RUSSIAN = "ru", "Russian"
    NEPALI = "ne", "Nepali"
    BURMESE = "my", "Burmese"
    CHINESE = "zh-hans", "Chinese"
    ARABIC = "ar", "Arabic"
    SWAHILI = "sw", "Swahili"
    POLISH = "pl", "Polish"
    TAGALOG = "tl", "Tagalog"
    KOREAN = "ko", "Korean"
    URDU = "ur", "Urdu"
    PORTUGUESE = "pt-br", "Portuguese"
    HAITIAN_CREOLE = "ht", "Haitian Creole"
    ALL = "ALL", "all languages"


# What the results page filter shows for each legal status a household picks, in button order.
_LEGAL_STATUS_TEXT: dict[str, tuple[str, str, str, str]] = {
    LegalStatusLabel.CITIZEN: (
        "citizenshipButton-citizen",
        "U.S. Citizen",
        "citizenshipTooltip-citizen",
        "U.S. citizens by birth or naturalization.",
    ),
    LegalStatusLabel.GC_5PLUS: (
        "citizenshipButton-gc_5plus",
        "Green Card 5+",
        "citizenshipTooltip-gc_5plus",
        "Lawful permanent residents who have had their green card for 5 or more years.",
    ),
    LegalStatusLabel.GC_5LESS: (
        "citizenshipButton-gc_5less",
        "Green Card <5",
        "citizenshipTooltip-gc_5less",
        "Lawful permanent residents who have had their green card for less than 5 years.",
    ),
    LegalStatusLabel.REFUGEE: (
        "citizenshipButton-refugee",
        "Refugee/Asylee",
        "citizenshipTooltip-refugee",
        "Individuals granted refugee or asylee status by the U.S. government.",
    ),
    LegalStatusLabel.OTHER_WITH_WORK_PERMISSION: (
        "citizenshipButton-otherLawful",
        "Other Lawful",
        "citizenshipTooltip-otherLawful",
        "Other lawfully present noncitizens with authorization to live or work in the U.S.",
    ),
    LegalStatusLabel.NON_CITIZEN: (
        "citizenshipButton-undocumented",
        "Undocumented",
        "citizenshipTooltip-undocumented",
        "Individuals without lawful immigration status (includes DACA recipients).",
    ),
}


def legal_status_options() -> dict[str, dict[str, dict[str, str]]]:
    """The legal statuses a household picks on the results page, with each button's label and tooltip."""
    return {
        str(status): {
            "label": {"_label": label_id, "_default_message": label},
            "tooltip": {"_label": tooltip_id, "_default_message": tooltip},
        }
        for status, (label_id, label, tooltip_id, tooltip) in _LEGAL_STATUS_TEXT.items()
    }


def navigator_language_options() -> dict[str, dict[str, str]]:
    """The badge the program page draws for each navigator language."""
    return {
        code: {
            "_label": f"navLanguage.{code}",
            "_default_message": (
                "All Languages Available" if code == NavigatorLanguageCode.ALL else f"{label} Available"
            ),
        }
        for code, label in NavigatorLanguageCode.choices
    }


def check_legal_status_label(label: str) -> None:
    """Raise `ValueError` unless `label` is a known legal status label."""
    if label not in LegalStatusLabel.values:
        raise ValueError(
            f"legal status '{label}' isn't a label the screener knows. Use one of "
            f"{', '.join(LegalStatusLabel.values)}."
        )


def check_navigator_language_code(code: str) -> None:
    """Raise `ValueError` unless `code` is a known navigator language code."""
    if code not in NavigatorLanguageCode.values:
        raise ValueError(
            f"navigator language '{code}' isn't one the screener shows. Use one of "
            f"{', '.join(NavigatorLanguageCode.values)}."
        )


def validate_legal_status_label(value: str) -> None:
    """Field validator for forms and `full_clean`."""
    try:
        check_legal_status_label(value)
    except ValueError as e:
        raise ValidationError(str(e)) from None


def validate_navigator_language_code(value: str) -> None:
    """Field validator for forms and `full_clean`."""
    try:
        check_navigator_language_code(value)
    except ValueError as e:
        raise ValidationError(str(e)) from None


def unknown_warning_calculator(name: str) -> bool:
    """Whether `name` isn't a registered warning calculator, so a warning using it would never show."""
    from programs.warnings import warning_calculators

    return name not in warning_calculators


def warning_calculator_choices() -> list[tuple[str, str]]:
    """The registered warning calculators, for a form's dropdown."""
    from programs.warnings import warning_calculators

    return [(name, name) for name in sorted(warning_calculators)]
