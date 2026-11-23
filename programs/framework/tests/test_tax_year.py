from datetime import date
from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.framework.base import ProgramCalculator


class TaxYearTests(SimpleTestCase):
    def _calculator(self, year):
        screen = Mock()
        screen.get_reference_date.return_value = date(2026, 9, 15)
        program = Mock()
        program.year = year
        return ProgramCalculator(screen, program, {}, Mock())

    def test_uses_the_program_year(self):
        self.assertEqual(self._calculator(Mock(period="2024")).tax_year, 2024)

    def test_without_a_program_year_uses_the_year_before_the_reference_date(self):
        self.assertEqual(self._calculator(None).tax_year, 2025)
