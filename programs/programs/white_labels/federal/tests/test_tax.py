"""The shared federal tax figures the federal credits read."""

from django.test import SimpleTestCase

from programs.programs.white_labels.federal.tax import FEDERAL_TAX_YEARS, HEAD_OF_HOUSEHOLD, JOINT, SINGLE


class TestFederalTaxYears(SimpleTestCase):
    def test_every_year_covers_every_filing_status(self):
        """Each credit looks a year's figures up by filing status. A status missing from one year
        raises for every household filing that way, which drops the credit for everyone."""
        statuses = {JOINT, HEAD_OF_HOUSEHOLD, SINGLE}
        for tax_year, figures in FEDERAL_TAX_YEARS.items():
            with self.subTest(tax_year=tax_year):
                self.assertEqual(set(figures.standard_deduction), statuses)
                self.assertEqual(set(figures.extra_deduction), statuses)
                self.assertEqual(set(figures.tax_brackets), statuses)
