"""
The lists `add_config` serves the screener, and the screener's copies of the lists it still keeps in
code because it holds logic per value.

The `SCREENER_*` sets below are copies of benefits-calculator's lists. Its
`src/Components/Config/apiServedLists.test.ts` pins its own lists to copies of this repo's, so a
value added on one side only fails CI on that side. Update both repos together.
"""

import json
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from configuration.models import Configuration
from configuration.white_labels import white_label_config
from programs.allowed_values import NavigatorLanguageCode, USER_SELECTED_LEGAL_STATUSES
from programs.models import Program
from screener.allowed_values import ACUTE_OPTION_FIELDS
from screener.models import Screen, WhiteLabel

# benefits-calculator: `ALL_VALID_WHITE_LABELS` (src/Types/WhiteLabel.ts)
SCREENER_WHITE_LABELS = {"co", "nc", "cesn", "ma", "il", "ks", "mo", "nj", "tx", "wa"}
# benefits-calculator: `Language` (src/Assets/languageOptions.tsx)
SCREENER_LANGUAGES = {
    "en-us",
    "es",
    "vi",
    "fr",
    "am",
    "so",
    "ru",
    "ne",
    "my",
    "zh-hans",
    "ar",
    "sw",
    "pl",
    "tl",
    "ko",
    "ur",
    "pt-br",
    "ht",
}
# benefits-calculator: `UI_OPTIONS` (src/Components/Referrer/uiOptions.ts)
SCREENER_UI_OPTIONS = {
    "211co",
    "211ks",
    "211mo",
    "211nc",
    "ccla",
    "dont_show_category_values",
    "hfed",
    "il_show_211_link",
    "lanc",
    "logo_landing_page_link",
    "nc_show_211_link",
    "no_confirmation_return_zipcode",
    "no_lets_get_started",
    "no_results_more_help",
    "no_zipcode_change_state",
    "powered_by_mfb_footer",
    "small_header_language_dropdown",
    "white_header",
}
# benefits-calculator: `OPTION_CARD_ICON_MAP` keys plus the energy calculator's own icons
# (src/Components/Config/configHook.tsx)
SCREENER_ICONS = {
    "None",
    "Employer",
    "PrivateInsurance",
    "Medicaid",
    "Medicare",
    "Chp",
    "Family_planning",
    "VA",
    "Student",
    "Pregnant",
    "BlindOrVisuallyImpaired",
    "Disabled",
    "LongTermDisability",
    "FosterCare",
    "Food",
    "Baby_supplies",
    "Housing",
    "Homeless_services",
    "Support",
    "Child_development",
    "Job_resources",
    "Dental_care",
    "Health_care",
    "Legal_services",
    "Savings",
    "Transportation",
    "Medical_expenses_and_debt",
    "Drug_alcohol_use",
    "Military",
    "Aging",
    "Youth_development",
    "SurvivingSpouse",
    "Wheelchair",
    "HeartRate",
}
# benefits-calculator: the `useValueFormats` keys other than `default` (src/Components/Results/FormattedValue.tsx)
SCREENER_VALUE_FORMATS = {"lump_sum", "estimated_annual"}


def _icons(value: Any) -> set[str]:
    """Every `_icon` name anywhere in a config value."""
    if isinstance(value, dict):
        found = {value["_icon"]} if "_icon" in value else set()
        return found.union(*(_icons(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(_icons(v) for v in value))
    return set()


def _config_values(config: Any) -> list[Any]:
    return [getattr(config, name) for name in dir(config) if not name.startswith("_")]


class ScreenerParityTests(SimpleTestCase):
    def test_white_labels_match_the_screener(self) -> None:
        self.assertEqual(set(white_label_config) - {"_default"}, SCREENER_WHITE_LABELS)

    def test_site_languages_match_the_screener(self) -> None:
        self.assertEqual({code for code, _ in settings.LANGUAGES}, SCREENER_LANGUAGES)

    def test_value_formats_match_the_screener(self) -> None:
        self.assertEqual({value for value, _ in Program.VALUE_FORMAT_CHOICES if value}, SCREENER_VALUE_FORMATS)

    def test_every_ui_option_is_one_the_screener_handles(self) -> None:
        for code, config in white_label_config.items():
            used = {flag for flags in config.referrer_data.get("uiOptions", {}).values() for flag in flags}
            with self.subTest(white_label=code):
                self.assertEqual(used - SCREENER_UI_OPTIONS, set())

    def test_every_icon_is_one_the_screener_draws(self) -> None:
        for code, config in white_label_config.items():
            used = set().union(*(_icons(value) for value in _config_values(config)))
            with self.subTest(white_label=code):
                self.assertEqual(used - SCREENER_ICONS, set())


class HouseholdNeedTests(SimpleTestCase):
    def test_every_offered_need_saves_to_a_screen_field(self) -> None:
        for code, config in white_label_config.items():
            with self.subTest(white_label=code):
                self.assertEqual(set(config.acute_condition_options) - set(ACUTE_OPTION_FIELDS), set())

        for field in ACUTE_OPTION_FIELDS.values():
            Screen._meta.get_field(field)


class AddConfigServesListsTests(TestCase):
    def setUp(self) -> None:
        WhiteLabel.objects.create(name="Default", code="_default")
        WhiteLabel.objects.create(name="CESN", code="cesn", state_code="CO")

    def _served(self, white_label: str, name: str) -> Any:
        data = Configuration.objects.get(white_label__code=white_label, name=name, active=True).data
        return json.loads(data) if isinstance(data, str) else data

    def test_every_white_label_gets_the_shared_lists(self) -> None:
        call_command("add_config", "_default", "cesn")

        for white_label in ("_default", "cesn"):
            with self.subTest(white_label=white_label):
                self.assertEqual(
                    list(self._served(white_label, "legal_status_options")),
                    ["citizen", "gc_5plus", "gc_5less", "refugee", "otherWithWorkPermission", "non_citizen"],
                )
                self.assertEqual(
                    set(self._served(white_label, "legal_status_options")),
                    {str(label) for label in USER_SELECTED_LEGAL_STATUSES},
                )
                self.assertEqual(
                    list(self._served(white_label, "navigator_language_options")), NavigatorLanguageCode.values
                )
                self.assertEqual(self._served(white_label, "acute_condition_fields"), ACUTE_OPTION_FIELDS)

    def test_the_energy_calculator_gets_its_expense_types(self) -> None:
        call_command("add_config", "cesn")

        self.assertEqual(
            list(self._served("cesn", "energy_calculator_expense_options")), ["heating", "cooling", "electricity"]
        )
