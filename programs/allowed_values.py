"""
The values benefits-api accepts for strings the screener interprets. Each list here is the one
authoritative source on the API side; every write path, the database constraints and the tests
read it.

Each list mirrors the screener, which holds the logic that gives a value meaning. Adding a value
takes a change in both repos, and a test on each side pins the two lists together:

- legal status labels: `CitizenLabels` in
  benefits-calculator/src/Components/Results/Filter/citizenshipFilterConfig.tsx
- navigator language codes: `allNavigatorLanguages` in
  benefits-calculator/src/Components/Results/ProgramPage/NavigatorLanguages.tsx

Warning calculators aren't listed here: the registry in `programs.warnings` is their list.
"""

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
    Languages a navigator can list. The program page draws a badge for each, and hides any other
    code. Each label is the badge's English words, which the assistant forwards as card content.
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
    CHINESE = "zh", "Chinese"
    ARABIC = "ar", "Arabic"
    SWAHILI = "sw", "Swahili"
    POLISH = "pl", "Polish"
    TAGALOG = "tl", "Tagalog"
    KOREAN = "ko", "Korean"
    URDU = "ur", "Urdu"
    PORTUGUESE = "pt-br", "Portuguese"
    HAITIAN_CREOLE = "ht", "Haitian Creole"
    ALL = "ALL", "all languages"


def unknown_warning_calculator(name: str) -> bool:
    """Whether `name` isn't a registered warning calculator, so a warning using it would never show."""
    from programs.warnings import warning_calculators

    return name not in warning_calculators


def warning_calculator_choices() -> list[tuple[str, str]]:
    """The registered warning calculators, for a form's dropdown."""
    from programs.warnings import warning_calculators

    return [(name, name) for name in sorted(warning_calculators)]
