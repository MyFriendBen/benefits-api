from datetime import date
from unittest.mock import patch

from django.test import TestCase

from programs.framework.base import Eligibility
from programs.models import FederalPoveryLimit, Program, WarningMessage
from programs.util import Dependencies
from programs.warnings import warning_calculators
from programs.warnings.base import fill_warning_placeholders
from programs.warnings.prior_tax_year import PriorTaxYear
from screener.models import Screen, WhiteLabel


class TestPriorTaxYear(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        cls.screen = Screen.objects.create(white_label=cls.white_label, zipcode="78701", completed=True)
        cls.program = Program.objects.new_program("test", "eitc")
        cls.warning = WarningMessage.objects.new_warning("test", "_prior_tax_year", external_name="prior_tax_year")
        cls.warning.programs.add(cls.program)

    def set_program_year(self, period):
        if period is None:
            self.program.year = None
        else:
            self.program.year, _ = FederalPoveryLimit.objects.get_or_create(year=period, defaults={"period": period})
        self.program.save()

    def shows(self, reference_date: date, program=None) -> bool:
        calculator = PriorTaxYear(
            self.screen, self.warning, Eligibility(), Dependencies(), program=program or self.program
        )
        with patch.object(Screen, "get_reference_date", return_value=reference_date):
            return calculator.calc()

    def test_registered(self):
        self.assertIs(warning_calculators["_prior_tax_year"], PriorTaxYear)

    def test_shows_when_the_program_is_on_last_year(self):
        self.set_program_year("2025")
        self.assertTrue(self.shows(date(2026, 9, 23)))

    def test_hidden_when_the_program_is_on_the_current_year(self):
        self.set_program_year("2026")
        self.assertFalse(self.shows(date(2026, 9, 23)))

    def test_hidden_when_the_program_is_two_years_back(self):
        self.set_program_year("2024")
        self.assertFalse(self.shows(date(2026, 9, 23)))

    def test_year_boundaries(self):
        """The message's {priorYear} rolls over on January 1, so the check must too."""
        self.set_program_year("2025")
        self.assertTrue(self.shows(date(2026, 1, 1)))
        self.assertTrue(self.shows(date(2026, 12, 31)))
        self.assertFalse(self.shows(date(2025, 12, 31)))
        self.assertFalse(self.shows(date(2027, 1, 1)))

    def test_hidden_without_a_program_year(self):
        self.set_program_year(None)
        self.assertFalse(self.shows(date(2026, 9, 23)))

    def test_hidden_without_a_program(self):
        calculator = PriorTaxYear(self.screen, self.warning, Eligibility(), Dependencies())
        with patch.object(Screen, "get_reference_date", return_value=date(2026, 9, 23)):
            self.assertFalse(calculator.calc())


class TestFillWarningPlaceholders(TestCase):
    def test_fills_both_years(self):
        text = "These results are for the {priorYear} tax year, due April 15, {currentYear}."
        self.assertEqual(
            fill_warning_placeholders(text, date(2026, 9, 23)),
            "These results are for the 2025 tax year, due April 15, 2026.",
        )

    def test_leaves_text_without_placeholders_alone(self):
        self.assertEqual(fill_warning_placeholders("Apply in person.", date(2026, 9, 23)), "Apply in person.")
