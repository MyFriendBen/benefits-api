from django.test import SimpleTestCase

from programs.models import FederalPoveryLimit
from programs.programs.shared.income import fpl_income_limit, table_income_limit


class TestFplIncomeLimit(SimpleTestCase):
    def setUp(self):
        # Unsaved: get_limit reads the FPL constant, not the database.
        self.fpl = FederalPoveryLimit(year="2025", period="2025")

    def test_scales_the_guideline_for_the_household_size(self):
        # 2025 guideline for 3 people is $26,650.
        self.assertEqual(fpl_income_limit(self.fpl, 3, 1.5), 39_975)

    def test_truncates_to_whole_dollars(self):
        # 1.85 x $15,650 = $28,952.50, truncated rather than rounded.
        self.assertEqual(fpl_income_limit(self.fpl, 1, 1.85), 28_952)

    def test_extends_past_the_largest_defined_size(self):
        # $54,150 for 8 plus $5,500 for the ninth person.
        self.assertEqual(fpl_income_limit(self.fpl, 9, 1), 59_650)

    def test_returns_an_int(self):
        self.assertIsInstance(fpl_income_limit(self.fpl, 2, 2.0), int)


class TestTableIncomeLimit(SimpleTestCase):
    TABLE = {1: 1_000, 2: 2_000, 3: 3_000}

    def test_reads_a_listed_size(self):
        self.assertEqual(table_income_limit(self.TABLE, 2, 500), 2_000)

    def test_extends_from_the_largest_listed_size(self):
        self.assertEqual(table_income_limit(self.TABLE, 5, 500), 4_000)

    def test_largest_size_is_found_regardless_of_key_order(self):
        self.assertEqual(table_income_limit({3: 3_000, 1: 1_000, 2: 2_000}, 4, 500), 3_500)
