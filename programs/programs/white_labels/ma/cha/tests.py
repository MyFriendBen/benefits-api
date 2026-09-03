"""Unit tests for the Cambridge Housing Authority (CHA) calculator.

Eligibility is a location gate plus an income gate: the household must be in Cambridge,
and its income must not exceed 80% of area median income. The AMI figure comes from HUD,
which these tests supply through `hud_ami` — HUD's own request building and error handling
are covered in `integrations/clients/hud_income_limits/tests`.
"""

from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.ma.cha.calculator import Cha


class TestCha(CustomCalculatorTestCase):
    """Test cases for Cambridge Housing Authority calculator"""

    calculator_class = Cha
    program_code = "ma_cha"
    white_label_code = "ma"
    state_code = "MA"
    # MA stores the city name in the county field (MFB-548).
    default_zipcode = "02138"
    default_county = "Cambridge"

    def setUp(self):
        super().setUp()
        self.eligible_screen = self.make_screen(household_size=2)
        self.head = self.add_member(
            self.eligible_screen, "headOfHousehold", 35, student=False, has_income=True, monthly_income=3000
        )

    def test_household_eligible_in_cambridge_below_income_limit(self):
        """Test household is eligible when in Cambridge and below 80% AMI"""
        with self.hud_ami(50000) as hud:
            eligibility = self.make_calculator(self.eligible_screen).eligible()

        self.assertTrue(eligibility.eligible)
        hud.get_screen_il_ami.assert_called_once_with(self.eligible_screen, "80%", "2025", county_override="Middlesex")

    def test_household_ineligible_outside_cambridge(self):
        """Test household is ineligible when not in Cambridge"""
        screen = self.make_screen(household_size=2, zipcode="02101", county="Boston")
        self.add_member(screen, "headOfHousehold", 35, has_income=True, monthly_income=3000)

        with self.hud_ami(50000):
            eligibility = self.make_calculator(screen).eligible()

        self.assertFalse(eligibility.eligible)

    def test_household_ineligible_income_too_high(self):
        """Test household is ineligible when income exceeds 80% AMI"""
        screen = self.make_screen(household_size=2)
        # $84,000/year - above limit
        self.add_member(screen, "headOfHousehold", 35, has_income=True, monthly_income=7000)

        with self.hud_ami(80000):
            eligibility = self.make_calculator(screen).eligible()

        self.assertFalse(eligibility.eligible)

    def test_household_eligible_income_at_limit(self):
        """Test household is eligible when income equals 80% AMI exactly"""
        with self.hud_ami(36000):
            eligibility = self.make_calculator(self.eligible_screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_value_returns_one(self):
        """Test that value returns 1 for eligible households (displays as 'Varies')"""
        with self.hud_ami(50000):
            calculator = self.make_calculator(self.eligible_screen)
            eligibility = calculator.eligible()
            calculator.value(eligibility)

        self.assertEqual(eligibility.value, 1)

    def test_eligibility_messages_on_failure(self):
        """Test that appropriate failure messages are added"""
        screen = self.make_screen(household_size=2, zipcode="02101", county="Boston")
        self.add_member(screen, "headOfHousehold", 35, has_income=True, monthly_income=3000)

        with self.hud_ami(30000):
            eligibility = self.make_calculator(screen).eligible()

        self.assertFalse(eligibility.eligible)
        self.assertTrue(len(eligibility.fail_messages) >= 1)

    def test_larger_household_size(self):
        """Test eligibility with larger household size"""
        screen = self.make_screen(household_size=5, zipcode="02139")
        self.add_member(screen, "headOfHousehold", 40, has_income=True, monthly_income=4000)
        for age in [5, 8, 12, 15]:
            self.add_member(screen, "child", age, has_income=False)

        with self.hud_ami(70000):
            eligibility = self.make_calculator(screen).eligible()

        self.assertTrue(eligibility.eligible)
