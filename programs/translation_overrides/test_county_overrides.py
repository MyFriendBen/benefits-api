"""
Tests for county-branched translation overrides — the mechanism that lets one
program serve a different "Apply Now" link depending on the household's county.

A program has one `apply_button_link`. A `TranslationOverride` row scoped to a set
of counties replaces it for screens in those counties; every other county falls
through to the program's own field, which is the default. Coverage here:

  1. TestTranslationOverrideCountyEligible - county_eligible() in isolation
  2. TestApplyButtonLinkByCounty           - get_translation() end to end
  3. TestCountyNameConventions             - the naming trap that makes a
                                             misconfigured override a silent no-op

County matching is exact string equality against `Screen.county`, and each white
label carries its own convention: Illinois stores bare names ("Cook"), while CO,
NC, and WA store the "X County" form. Note this is stricter than the substring
test navigator filtering uses in `filter_by_county`, so a value that resolves a
navigator can still fail to resolve an override.
"""

from django.conf import settings
from django.test import TestCase

from programs.models import County, Program, TranslationOverride
from programs.translation_overrides import warning_calculators
from programs.translation_overrides.base import TranslationOverrideCalculator
from programs.util import Dependencies
from screener.models import Screen, WhiteLabel

CEDA_LINK = "https://www.cedaorg.net/en/find-services/gas-and-electric"
DEFAULT_LIHEAP_LINK = "https://example.org/apply/il-liheap"


def set_translation(translated_field, text: str) -> None:
    """Set a Translation's text in the default language.

    `new_program` leaves every translation at BLANK_TRANSLATION_PLACEHOLDER, so a
    test that asserts on a real URL has to fill it in. These are django-parler
    models, so the write has to target an explicit language.
    """
    translated_field.set_current_language(settings.LANGUAGE_CODE)
    translated_field.text = text
    translated_field.save()


def get_translation_text(translation) -> str:
    """Read a Translation's text in the default language."""
    translation.set_current_language(settings.LANGUAGE_CODE)
    return translation.text


class TestTranslationOverrideCountyEligible(TestCase):
    """Unit tests for TranslationOverrideCalculator.county_eligible()."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="IL Test", code="il_test", state_code="IL")
        cls.cook = County.objects.create(name="Cook", white_label=cls.white_label)
        cls.dupage = County.objects.create(name="DuPage", white_label=cls.white_label)
        cls.program = Program.objects.new_program("il_test", "il_liheap_test")

    def setUp(self):
        self.override = TranslationOverride.objects.new_translation_override("il_test", "_show", "apply_button_link")
        self.override.program = self.program
        self.override.save()

    def _calculator(self, county: str | None) -> TranslationOverrideCalculator:
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="60004", county=county, household_size=1, completed=False
        )
        return TranslationOverrideCalculator(screen, self.override, Dependencies())

    def test_matching_county_is_eligible(self):
        """Screen in a listed county gets the override."""
        self.override.counties.set([self.cook])
        self.assertTrue(self._calculator("Cook").county_eligible())

    def test_unlisted_county_is_not_eligible(self):
        """Screen outside the listed counties falls through to the default link."""
        self.override.counties.set([self.cook])
        self.assertFalse(self._calculator("DuPage").county_eligible())

    def test_no_counties_applies_everywhere(self):
        """An override with no counties is unscoped and applies to every screen."""
        self.override.counties.clear()
        self.assertTrue(self._calculator("DuPage").county_eligible())

    def test_blank_county_falls_through(self):
        """A screen with no county resolved cannot match a county-scoped override."""
        self.override.counties.set([self.cook])
        self.assertFalse(self._calculator(None).county_eligible())

    def test_multiple_counties_match_any(self):
        """Listing several counties matches a screen in any one of them."""
        self.override.counties.set([self.cook, self.dupage])
        self.assertTrue(self._calculator("Cook").county_eligible())
        self.assertTrue(self._calculator("DuPage").county_eligible())

    def test_show_calculator_defers_entirely_to_county(self):
        """`_show` adds no eligibility rule of its own, so calc() is the county test.

        This is what makes a plain county-branched link possible with no new code.
        """
        self.override.counties.set([self.cook])
        self.assertIs(warning_calculators["_show"], TranslationOverrideCalculator)
        self.assertTrue(self._calculator("Cook").calc())
        self.assertFalse(self._calculator("DuPage").calc())


class TestApplyButtonLinkByCounty(TestCase):
    """End-to-end tests for a county-specific apply_button_link via get_translation()."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="IL Test", code="il_test", state_code="IL")
        cls.cook = County.objects.create(name="Cook", white_label=cls.white_label)
        cls.program = Program.objects.new_program("il_test", "il_liheap_e2e")
        set_translation(cls.program.apply_button_link, DEFAULT_LIHEAP_LINK)

    def setUp(self):
        self.override = TranslationOverride.objects.new_translation_override("il_test", "_show", "apply_button_link")
        self.override.program = self.program
        self.override.save()
        self.override.counties.set([self.cook])
        set_translation(self.override.translation, CEDA_LINK)

    def _link_for(self, county: str | None) -> str:
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="60004", county=county, household_size=1, completed=False
        )
        program = Program.objects.get(pk=self.program.pk)
        return get_translation_text(program.get_translation(screen, Dependencies(), "apply_button_link"))

    def test_cook_county_gets_ceda_link(self):
        self.assertEqual(self._link_for("Cook"), CEDA_LINK)

    def test_other_county_gets_default_link(self):
        """The program's own field is the fallback — no default row is configured."""
        self.assertEqual(self._link_for("DuPage"), DEFAULT_LIHEAP_LINK)

    def test_inactive_override_is_ignored(self):
        self.override.active = False
        self.override.save()
        self.assertEqual(self._link_for("Cook"), DEFAULT_LIHEAP_LINK)

    def test_override_only_affects_its_own_field(self):
        """An apply_button_link override must not change learn_more_link."""
        set_translation(self.program.learn_more_link, "https://example.org/learn")
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="60004", county="Cook", household_size=1, completed=False
        )
        program = Program.objects.get(pk=self.program.pk)
        self.assertEqual(
            get_translation_text(program.get_translation(screen, Dependencies(), "learn_more_link")),
            "https://example.org/learn",
        )

    def test_program_without_override_is_unaffected(self):
        """Single-link programs keep working with no config change."""
        other = Program.objects.new_program("il_test", "il_other_program")
        set_translation(other.apply_button_link, "https://example.org/apply/other")
        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="60004", county="Cook", household_size=1, completed=False
        )
        self.assertEqual(
            get_translation_text(other.get_translation(screen, Dependencies(), "apply_button_link")),
            "https://example.org/apply/other",
        )


class TestCountyNameConventions(TestCase):
    """County matching is exact, and the right string differs per white label.

    A county name in the wrong convention makes the override a silent no-op: no
    error, no log line, just the default link everywhere. These tests pin the
    behavior so a misconfiguration fails here instead of in production.
    """

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="IL Test", code="il_test", state_code="IL")
        cls.program = Program.objects.new_program("il_test", "il_liheap_naming")
        set_translation(cls.program.apply_button_link, DEFAULT_LIHEAP_LINK)

    def _link_for_override_county(self, override_county: str, screen_county: str) -> str:
        county = County.objects.create(name=override_county, white_label=self.white_label)
        override = TranslationOverride.objects.new_translation_override("il_test", "_show", "apply_button_link")
        override.program = self.program
        override.save()
        override.counties.set([county])
        set_translation(override.translation, CEDA_LINK)

        screen = Screen.objects.create(
            white_label=self.white_label, zipcode="60004", county=screen_county, household_size=1, completed=False
        )
        program = Program.objects.get(pk=self.program.pk)
        return get_translation_text(program.get_translation(screen, Dependencies(), "apply_button_link"))

    def test_il_bare_county_name_resolves(self):
        """Illinois stores bare county names, so "Cook" is the correct value."""
        self.assertEqual(self._link_for_override_county("Cook", "Cook"), CEDA_LINK)

    def test_il_county_suffix_silently_fails_to_resolve(self):
        """ "Cook County" never matches an IL screen — the documented wrong value.

        Matching is equality, not the substring test used for navigators, so the
        suffix form yields the default link with no error.
        """
        self.assertEqual(self._link_for_override_county("Cook County", "Cook"), DEFAULT_LIHEAP_LINK)

    def test_suffix_convention_resolves_where_screens_use_it(self):
        """CO/NC/WA store the "X County" form, where the suffix is correct."""
        self.assertEqual(
            self._link_for_override_county("Denver County", "Denver County"),
            CEDA_LINK,
        )
