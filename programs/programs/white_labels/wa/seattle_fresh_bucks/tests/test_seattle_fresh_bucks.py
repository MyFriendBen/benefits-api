from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from screener.models import IncomeStream
from programs.programs.white_labels.wa.seattle_fresh_bucks.calculator import WaSeattleFreshBucks


class TestWaSeattleFreshBucks(CustomCalculatorTestCase):
    calculator_class = WaSeattleFreshBucks
    program_code = "wa_seattle_fresh_bucks"
    white_label_code = "wa"
    state_code = "WA"
    default_zipcode = "98103"
    default_county = "King County"

    def setUp(self):
        super().setUp()
        self.screen = self.make_screen(household_size=1)
        self.head = self.add_member(self.screen, "headOfHousehold", 30, has_income=True, monthly_income=2500)

    def create_calculator(self, screen=None):
        return self.make_calculator(screen or self.screen)

    # --- Class attributes ---

    def test_amount_is_yearly(self):
        self.assertEqual(WaSeattleFreshBucks.amount, 60 * 12)

    def test_min_age_is_18(self):
        self.assertEqual(WaSeattleFreshBucks.min_age, 18)

    def test_max_ami_percent_is_80(self):
        self.assertEqual(WaSeattleFreshBucks.max_ami_percent, "80%")

    # --- Location ---

    def test_eligible_seattle_zip(self):
        with self.hud_ami(100_000):
            calc = self.create_calculator()
            self.assertTrue(calc.eligible().eligible)

    def test_ineligible_non_seattle_zip(self):
        with self.hud_ami(100_000):
            self.screen.zipcode = "98004"  # Bellevue
            self.screen.save()
            calc = self.create_calculator()
            self.assertFalse(calc.eligible().eligible)

    def test_all_test_scenario_zips_are_seattle(self):
        with self.hud_ami(100_000):
            for zipcode in ["98103", "98118", "98144", "98122"]:
                self.screen.zipcode = zipcode
                self.screen.save()
                calc = self.create_calculator()
                self.assertTrue(calc.eligible().eligible, f"Expected {zipcode} to be eligible")

    # --- Age ---

    def test_eligible_head_age_18(self):
        with self.hud_ami(100_000):
            self.head.age = 18
            self.head.save()
            calc = self.create_calculator()
            self.assertTrue(calc.eligible().eligible)

    def test_ineligible_head_age_17(self):
        with self.hud_ami(100_000):
            self.head.age = 17
            self.head.save()
            calc = self.create_calculator()
            self.assertFalse(calc.eligible().eligible)

    def test_eligible_senior_head(self):
        with self.hud_ami(100_000):
            self.head.age = 72
            self.head.save()
            calc = self.create_calculator()
            self.assertTrue(calc.eligible().eligible)

    def test_ineligible_head_age_none(self):
        with self.hud_ami(100_000):
            self.head.age = None
            self.head.save()
            calc = self.create_calculator()
            self.assertFalse(calc.eligible().eligible)

    # --- Income ---

    def test_eligible_income_below_ami(self):
        # 80% AMI 1-person
        with self.hud_ami(84_850):
            calc = self.create_calculator()
            self.assertTrue(calc.eligible().eligible)

    def test_eligible_income_exactly_at_ami(self):
        with self.hud_ami(84_852):
            # $7,071/mo × 12 = $84,852/yr; limit set to match exactly
            IncomeStream.objects.filter(screen=self.screen).update(amount=7071, frequency="monthly")
            calc = self.create_calculator()
            self.assertTrue(calc.eligible().eligible)

    def test_ineligible_income_above_ami(self):
        # $7,072/mo × 12 = $84,864 > $84,850
        with self.hud_ami(84_850):
            IncomeStream.objects.filter(screen=self.screen).update(amount=7072, frequency="monthly")
            calc = self.create_calculator()
            self.assertFalse(calc.eligible().eligible)

    def test_eligible_zero_income(self):
        with self.hud_ami(84_850):
            IncomeStream.objects.filter(screen=self.screen).delete()
            self.head.has_income = False
            self.head.save()
            calc = self.create_calculator()
            self.assertTrue(calc.eligible().eligible)

    def test_ineligible_on_hud_client_error(self):
        with self.hud_ami(unavailable=True):
            calc = self.create_calculator()
            self.assertFalse(calc.eligible().eligible)

    def test_hud_client_called_with_correct_args(self):
        with self.hud_ami(100_000) as mock_hud:
            calc = self.create_calculator()
            calc.eligible()
            mock_hud.get_screen_il_ami.assert_called_once_with(self.screen, "80%", "2025")

    # --- Benefit value ---

    def test_value_is_yearly_when_eligible(self):
        with self.hud_ami(100_000):
            calc = self.create_calculator()
            e = calc.eligible()
            calc.value(e)
            self.assertEqual(e.value, 60 * 12)

    def test_value_is_household_level_not_per_member(self):
        """Multi-adult household still gets a single $60/mo ($720/yr) benefit."""
        with self.hud_ami(200_000):
            self.screen.household_size = 2
            self.screen.save()
            self.add_member(self.screen, "spouse", 28, has_income=False)
            calc = self.create_calculator()
            e = calc.eligible()
            calc.value(e)
            self.assertEqual(e.value, 60 * 12)

    def test_value_is_0_when_ineligible(self):
        with self.hud_ami(100_000):
            self.screen.zipcode = "98004"
            self.screen.save()
            calc = self.create_calculator()
            e = calc.eligible()
            calc.value(e)
            self.assertEqual(e.value, 0)
