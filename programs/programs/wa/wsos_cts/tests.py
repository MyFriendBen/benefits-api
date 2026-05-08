from unittest.mock import Mock

from django.test import TestCase

from programs.programs.wa.wsos_cts.calculator import WaWsosCts
from programs.util import Dependencies
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel


class TestWaWsosCts(TestCase):
    """Unit tests for WA WSOS Career & Technical Scholarship (CTS)."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Washington", code="wa", state_code="WA")
        self.mock_program = Mock()

    def _make_screen(self, household_size=1, zipcode="98101", county="King"):
        return Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode=zipcode,
            county=county,
            household_size=household_size,
            completed=False,
        )

    def _add_member(self, screen, *, age=20, relationship="headOfHousehold", student=False, monthly_wages=0):
        member = HouseholdMember.objects.create(
            screen=screen,
            relationship=relationship,
            age=age,
            student=student,
        )
        if monthly_wages:
            IncomeStream.objects.create(
                screen=screen,
                household_member=member,
                type="wages",
                amount=monthly_wages,
                frequency="monthly",
            )
        return member

    def _calc(self, screen):
        return WaWsosCts(screen, self.mock_program, {}, Dependencies())

    def test_registered_in_wa_calculators(self):
        from programs.programs.wa import wa_calculators

        self.assertIn("wa_wsos_cts", wa_calculators)
        self.assertIs(wa_calculators["wa_wsos_cts"], WaWsosCts)

    def test_no_published_lump_sum_value(self):
        self.assertEqual(WaWsosCts.amount, 0)

    def test_dependencies(self):
        self.assertIn("income_amount", WaWsosCts.dependencies)
        self.assertIn("income_frequency", WaWsosCts.dependencies)
        self.assertIn("household_size", WaWsosCts.dependencies)

    # --- spec.md scenarios ---------------------------------------------------

    def test_scenario_1_eligible_student_below_mfi(self):
        """Scenario 1: student, $2,500/mo — under 1-person 125% MFI."""
        screen = self._make_screen()
        self._add_member(screen, age=24, student=True, monthly_wages=2500)
        self.assertTrue(self._calc(screen).eligible().eligible)

    def test_scenario_2_ineligible_not_a_student(self):
        """Scenario 2: not a student."""
        screen = self._make_screen()
        self._add_member(screen, age=36, student=False, monthly_wages=3000)
        self.assertFalse(self._calc(screen).eligible().eligible)

    def test_scenario_3_ineligible_income_above_mfi(self):
        """Scenario 3: student, $8,000/mo — above 125% MFI (no expanded path)."""
        screen = self._make_screen()
        self._add_member(screen, age=24, student=True, monthly_wages=8000)
        self.assertFalse(self._calc(screen).eligible().eligible)

    def test_scenario_4_three_person_at_exact_mfi_boundary(self):
        """Scenario 4: 3-person HH, $12,208/mo = $146,500/yr exactly — eligible."""
        screen = self._make_screen(household_size=3, zipcode="98501", county="Thurston")
        self._add_member(screen, age=31, student=True, monthly_wages=12208)
        self._add_member(screen, relationship="spouse", age=30, student=False)
        self._add_member(screen, relationship="child", age=3, student=False)
        self.assertTrue(self._calc(screen).eligible().eligible)

    def test_scenario_5_rji_candidate_still_cts_eligible(self):
        """Scenario 5: Whatcom, 2p, combined income under 2-person cap."""
        screen = self._make_screen(household_size=2, zipcode="98225", county="Whatcom")
        self._add_member(screen, age=23, student=True, monthly_wages=3500)
        self._add_member(screen, relationship="parent", age=51, student=False, monthly_wages=1500)
        self.assertTrue(self._calc(screen).eligible().eligible)

    def test_scenario_6_four_person_above_mfi(self):
        """Scenario 6: student head $15k/mo only — over 4-person 125% MFI."""
        screen = self._make_screen(household_size=4, zipcode="98501", county="Thurston")
        self._add_member(screen, age=36, student=True, monthly_wages=15000)
        self._add_member(screen, relationship="spouse", age=34, student=False)
        self._add_member(screen, relationship="child", age=7, student=False)
        self._add_member(screen, relationship="child", age=5, student=False)
        self.assertFalse(self._calc(screen).eligible().eligible)

    def test_eligible_when_only_dependent_is_student(self):
        """Head not a student but a child is — base class requires one eligible member."""
        screen = self._make_screen(household_size=2)
        self._add_member(screen, age=40, student=False, monthly_wages=4000)
        self._add_member(screen, relationship="child", age=18, student=True, monthly_wages=0)
        self.assertTrue(self._calc(screen).eligible().eligible)

    def test_income_slightly_above_limit_rejected(self):
        """Fractional excess above 125% cap must not pass (4p: $174,500.50 / year)."""
        screen = self._make_screen(household_size=4)
        self._add_member(screen, student=True, monthly_wages=(174_500.50 / 12))
        self._add_member(screen, relationship="spouse", student=False)
        self._add_member(screen, relationship="child", age=10, student=False)
        self._add_member(screen, relationship="child", age=8, student=False)
        self.assertFalse(self._calc(screen).eligible().eligible)

    def test_mfi_linear_extension_size_7(self):
        """Sizes above 6 extend by $28k per extra person (same rule as BaS)."""
        calc = WaWsosCts(self._make_screen(household_size=7), self.mock_program, {}, Dependencies())
        self.assertEqual(calc.income_limit_125(), 230_000 + 28_000)

    # --- Value ----------------------------------------------------------------

    def test_value_zero_when_eligible(self):
        screen = self._make_screen()
        self._add_member(screen, student=True, monthly_wages=2500)
        calc = self._calc(screen)
        e = calc.eligible()
        calc.value(e)
        self.assertEqual(e.value, 0)

    def test_mfi_table_matches_spec(self):
        self.assertEqual(
            WaWsosCts.MFI_125_BY_SIZE,
            {1: 90_500, 2: 118_000, 3: 146_500, 4: 174_500, 5: 202_000, 6: 230_000},
        )
