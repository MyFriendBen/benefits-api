from django.test import TestCase
from unittest.mock import patch

from programs.programs.wa.seattle_fresh_bucks.calculator import WaSeattleFreshBucks
from screener.models import Screen, HouseholdMember, IncomeStream, WhiteLabel
from programs.models import Program, FederalPoveryLimit
from programs.util import Dependencies


class TestWaSeattleFreshBucks(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.wa_white_label = WhiteLabel.objects.create(name="Washington", code="wa", state_code="WA")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")
        cls.program = Program.objects.new_program(white_label="wa", name_abbreviated="wa_seattle_fresh_bucks")
        cls.program.year = cls.fpl_year
        cls.program.save()

    def setUp(self):
        self.screen = Screen.objects.create(
            agree_to_tos=True,
            zipcode="98103",
            county="King County",
            household_size=1,
            white_label=self.wa_white_label,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=30,
            has_income=True,
        )
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=2500,
            frequency="monthly",
        )

    def create_calculator(self, screen=None):
        return WaSeattleFreshBucks(screen or self.screen, self.program, {}, Dependencies())

    # --- Class attributes ---

    def test_registered_in_wa_calculators(self):
        from programs.programs.wa import wa_calculators

        self.assertIn("wa_seattle_fresh_bucks", wa_calculators)
        self.assertIs(wa_calculators["wa_seattle_fresh_bucks"], WaSeattleFreshBucks)

    def test_amount_is_60(self):
        self.assertEqual(WaSeattleFreshBucks.amount, 60)

    def test_min_age_is_18(self):
        self.assertEqual(WaSeattleFreshBucks.min_age, 18)

    def test_max_ami_percent_is_80(self):
        self.assertEqual(WaSeattleFreshBucks.max_ami_percent, "80%")

    # --- Location ---

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_eligible_seattle_zip(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 100_000
        calc = self.create_calculator()
        self.assertTrue(calc.eligible().eligible)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_ineligible_non_seattle_zip(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 100_000
        self.screen.zipcode = "98004"  # Bellevue
        self.screen.save()
        calc = self.create_calculator()
        self.assertFalse(calc.eligible().eligible)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_all_test_scenario_zips_are_seattle(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 100_000
        for zipcode in ["98103", "98118", "98144", "98122"]:
            self.screen.zipcode = zipcode
            self.screen.save()
            calc = self.create_calculator()
            self.assertTrue(calc.eligible().eligible, f"Expected {zipcode} to be eligible")

    # --- Age ---

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_eligible_head_age_18(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 100_000
        self.head.age = 18
        self.head.save()
        calc = self.create_calculator()
        self.assertTrue(calc.eligible().eligible)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_ineligible_head_age_17(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 100_000
        self.head.age = 17
        self.head.save()
        calc = self.create_calculator()
        self.assertFalse(calc.eligible().eligible)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_eligible_senior_head(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 100_000
        self.head.age = 72
        self.head.save()
        calc = self.create_calculator()
        self.assertTrue(calc.eligible().eligible)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_ineligible_head_age_none(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 100_000
        self.head.age = None
        self.head.save()
        calc = self.create_calculator()
        self.assertFalse(calc.eligible().eligible)

    # --- Income ---

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_eligible_income_below_ami(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 84_850  # 80% AMI 1-person
        calc = self.create_calculator()
        self.assertTrue(calc.eligible().eligible)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_eligible_income_exactly_at_ami(self, mock_hud):
        # $7,071/mo × 12 = $84,852/yr; limit set to match exactly
        IncomeStream.objects.filter(screen=self.screen).update(amount=7071, frequency="monthly")
        mock_hud.get_screen_il_ami.return_value = 84_852
        calc = self.create_calculator()
        self.assertTrue(calc.eligible().eligible)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_ineligible_income_above_ami(self, mock_hud):
        IncomeStream.objects.filter(screen=self.screen).update(amount=7072, frequency="monthly")
        mock_hud.get_screen_il_ami.return_value = 84_850  # $7,072/mo × 12 = $84,864 > $84,850
        calc = self.create_calculator()
        self.assertFalse(calc.eligible().eligible)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_eligible_zero_income(self, mock_hud):
        IncomeStream.objects.filter(screen=self.screen).delete()
        self.head.has_income = False
        self.head.save()
        mock_hud.get_screen_il_ami.return_value = 84_850
        calc = self.create_calculator()
        self.assertTrue(calc.eligible().eligible)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_ineligible_on_hud_client_error(self, mock_hud):
        from integrations.clients.hud_income_limits import HudIncomeClientError

        mock_hud.get_screen_il_ami.side_effect = HudIncomeClientError("API unavailable")
        calc = self.create_calculator()
        self.assertFalse(calc.eligible().eligible)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_hud_client_called_with_correct_args(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 100_000
        calc = self.create_calculator()
        calc.eligible()
        mock_hud.get_screen_il_ami.assert_called_once_with(self.screen, "80%", "2025")

    # --- Benefit value ---

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_value_is_60_when_eligible(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 100_000
        calc = self.create_calculator()
        e = calc.eligible()
        calc.value(e)
        self.assertEqual(e.value, 60)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_value_is_household_level_not_per_member(self, mock_hud):
        """Multi-adult household still gets a single $60 benefit."""
        mock_hud.get_screen_il_ami.return_value = 200_000
        self.screen.household_size = 2
        self.screen.save()
        HouseholdMember.objects.create(
            screen=self.screen,
            relationship="spouse",
            age=28,
            has_income=False,
        )
        calc = self.create_calculator()
        e = calc.eligible()
        calc.value(e)
        self.assertEqual(e.value, 60)

    @patch("programs.programs.wa.seattle_fresh_bucks.calculator.hud_client")
    def test_value_is_0_when_ineligible(self, mock_hud):
        mock_hud.get_screen_il_ami.return_value = 100_000
        self.screen.zipcode = "98004"
        self.screen.save()
        calc = self.create_calculator()
        e = calc.eligible()
        calc.value(e)
        self.assertEqual(e.value, 0)
