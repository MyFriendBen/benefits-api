"""
New Jersey income tax helpers. The Tax Table rows below are copied from the 2025 NJ-1040
instructions (page 54), so the midpoint pricing is checked against what a filer reads.
"""

from decimal import Decimal

from django.test import SimpleTestCase

from programs.programs.white_labels.nj.income_tax import TABLE_A, TABLE_B, income_tax, schedule_tax


class TestTaxTable(SimpleTestCase):
    # (row start, Table A tax, Table B tax) from the 2025 Tax Table.
    rows = [
        (0, 0, 0),
        (50, 1, 1),
        (100, 2, 2),
        (150, 2, 2),
        (17_000, 238, 238),
        (19_950, 280, 280),
        (20_000, 280, 280),
        (39_850, 713, 628),
        (70_050, 2_379, 1_298),
        (70_100, 2_382, 1_299),
        (99_950, 4_242, 2_749),
    ]

    def test_rows_are_priced_at_their_midpoint(self):
        for start, table_a, table_b in self.rows:
            for amount in (start, start + Decimal("49.99")):
                with self.subTest(amount=amount):
                    self.assertEqual(income_tax(Decimal(amount), TABLE_A), table_a)
                    self.assertEqual(income_tax(Decimal(amount), TABLE_B), table_b)

    def test_the_tax_table_uses_1155_in_table_b_70000_to_80000_row(self):
        # The statute's 1,154.50 would price this row at 1,300.
        self.assertEqual(income_tax(Decimal(70_100), TABLE_B), 1_299)

    def test_the_rate_schedule_applies_from_100000(self):
        self.assertEqual(income_tax(Decimal(100_000), TABLE_A), Decimal("4243.75"))
        self.assertEqual(income_tax(Decimal("142000"), TABLE_B), Decimal("5070.50"))

    def test_no_income_is_no_tax(self):
        self.assertEqual(income_tax(Decimal(0), TABLE_A), 0)
        self.assertEqual(income_tax(Decimal(-5), TABLE_B), 0)


class TestRateSchedules(SimpleTestCase):
    def test_bands_meet_where_they_join(self):
        """Each band's tax at its top equals the next band's at the same income."""
        for table in (TABLE_A, TABLE_B):
            for lower, upper in zip(table, table[1:]):
                top = Decimal(lower.top)
                with self.subTest(top=top):
                    self.assertEqual(top * lower.rate - lower.subtract, top * upper.rate - upper.subtract)

    def test_top_band_has_no_ceiling(self):
        self.assertEqual(schedule_tax(Decimal(2_000_000), TABLE_A), Decimal("182073.75"))
