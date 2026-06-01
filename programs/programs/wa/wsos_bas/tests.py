from unittest.mock import Mock

from django.test import TestCase

from programs.programs.wa.wsos_bas.calculator import WaWsosBas
from programs.util import Dependencies
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel


class TestWaWsosBas(TestCase):
    """
    Unit tests for the WA WSOS Baccalaureate (BaS) Scholarship calculator.

    Covers the two screener-checkable gates (at least one student, household
    annual income <= 125% MFI for size), the 2026 published table boundaries,
    the linear extension for households above the table, and the lump-sum
    value contract.

    Maps to spec.md scenarios but calls the calculator directly. The full
    end-to-end browser flow is exercised separately via Playwright; the
    persisted validation suite (`wa_wsos_bas.json`) covers Scenarios 1, 2,
    and 3 against the live screener layer.
    """

    def setUp(self):
        """Create a WA white label and a mock Program for each test."""
        self.white_label = WhiteLabel.objects.create(name="Washington", code="wa", state_code="WA")
        self.mock_program = Mock()

    def _make_screen(self, household_size=1, zipcode="98101", county="King"):
        """Build an in-memory `Screen` for the WA white label with the given size."""
        return Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode=zipcode,
            county=county,
            household_size=household_size,
            completed=False,
        )

    def _add_member(self, screen, *, age=20, relationship="headOfHousehold", student=False, monthly_wages=0):
        """Add a `HouseholdMember` (and optional monthly wages) to the screen."""
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
        """Construct a `WaWsosBas` calculator bound to the given screen."""
        return WaWsosBas(screen, self.mock_program, {}, Dependencies())

    # --- Class wiring --------------------------------------------------------

    def test_registered_in_wa_calculators(self):
        """Calculator is registered in the WA program registry under wa_wsos_bas."""
        from programs.programs.wa import wa_calculators

        self.assertIn("wa_wsos_bas", wa_calculators)
        self.assertIs(wa_calculators["wa_wsos_bas"], WaWsosBas)

    def test_amount_is_22500_lump_sum(self):
        """The published BaS lump-sum award is $22,500."""
        self.assertEqual(WaWsosBas.amount, 22_500)

    def test_dependencies_cover_income_and_household_size(self):
        """The calculator declares the screener fields it actually reads."""
        self.assertIn("income_amount", WaWsosBas.dependencies)
        self.assertIn("income_frequency", WaWsosBas.dependencies)
        self.assertIn("household_size", WaWsosBas.dependencies)

    # --- Eligibility (spec scenarios) ----------------------------------------

    def test_eligible_single_student_well_below_125_pct_mfi(self):
        """
        spec.md Scenario 1: WA student, 1-person household, $2k/mo wages
        ($24k/yr) — well below the 1-person 125% MFI cap of $90,500/yr.
        """
        screen = self._make_screen()
        self._add_member(screen, student=True, monthly_wages=2000)

        eligibility = self._calc(screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_ineligible_single_student_above_125_pct_mfi(self):
        """
        spec.md Scenario 2: WA student, 1-person household, $8k/mo
        ($96k/yr) — above the 1-person 125% MFI cap of $90,500/yr.
        BaS has no expanded / hardship band, so this fails income.
        """
        screen = self._make_screen()
        self._add_member(screen, student=True, monthly_wages=8000)

        eligibility = self._calc(screen).eligible()

        self.assertFalse(eligibility.eligible)

    def test_eligible_four_person_household_just_below_125_pct_mfi(self):
        """
        spec.md Scenario 3: 4-person family, HS-senior student applicant,
        $14,541/mo wages ($174,492/yr) -- just under the 4-person 125%
        MFI cap of $174,500/yr (monthly rounding edge).
        """
        screen = self._make_screen(household_size=4, zipcode="98501", county="Thurston")
        self._add_member(screen, age=46, monthly_wages=14541)
        self._add_member(screen, relationship="spouse", age=44, student=False)
        self._add_member(screen, relationship="child", age=17, student=True)
        self._add_member(screen, relationship="child", age=13, student=False)

        eligibility = self._calc(screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_ineligible_four_person_household_above_125_pct_mfi(self):
        """
        spec.md Scenario 4: same 4-person family, but $16k/mo
        ($192k/yr) -- well above the 4-person 125% MFI cap of $174,500/yr.
        """
        screen = self._make_screen(household_size=4, zipcode="98501", county="Thurston")
        self._add_member(screen, age=46, monthly_wages=16000)
        self._add_member(screen, relationship="spouse", age=44, student=False)
        self._add_member(screen, relationship="child", age=17, student=True)
        self._add_member(screen, relationship="child", age=13, student=False)

        eligibility = self._calc(screen).eligible()

        self.assertFalse(eligibility.eligible)

    def test_eligible_returning_adult_student_as_head_with_dependents(self):
        """
        spec.md Scenario 5: Returning adult student (age 28) is HoH and BaS
        applicant; non-student spouse + young child still count toward
        household size and income. $4k/mo wages ($48k/yr) -- well under
        the 3-person 125% MFI cap of $146,500/yr.
        """
        screen = self._make_screen(household_size=3, zipcode="99201", county="Spokane")
        self._add_member(screen, age=28, student=True, monthly_wages=4000)
        self._add_member(screen, relationship="spouse", age=30, student=False)
        self._add_member(screen, relationship="child", age=4, student=False)

        eligibility = self._calc(screen).eligible()

        self.assertTrue(eligibility.eligible)

    # --- Eligibility (extra coverage beyond the spec scenarios) --------------

    def test_ineligible_no_student_in_household(self):
        """
        Household with no student fails the per-member gate; the base
        ProgramCalculator auto-marks the household ineligible when no
        member passes member_eligible().
        """
        screen = self._make_screen()
        self._add_member(screen, age=46, student=False, monthly_wages=2000)

        eligibility = self._calc(screen).eligible()

        self.assertFalse(eligibility.eligible)

    def test_ineligible_when_student_field_is_unanswered(self):
        """
        `Screen.student` is BooleanField(null=True), so an unanswered field
        comes through as None. `bool(None) -> False -> ineligible`. Pinning
        this explicitly catches a future refactor that might confuse `is False`
        with a generic falsy check.
        """
        screen = self._make_screen()
        member = HouseholdMember.objects.create(
            screen=screen,
            relationship="headOfHousehold",
            age=20,
            student=None,
        )
        IncomeStream.objects.create(
            screen=screen,
            household_member=member,
            type="wages",
            amount=2000,
            frequency="monthly",
        )

        eligibility = self._calc(screen).eligible()

        self.assertFalse(eligibility.eligible)

    def test_eligible_zero_income_student(self):
        """
        Common BaS persona: unemployed student (e.g. HS senior pre-application)
        with zero household income. Lower-side income boundary, complementing
        `test_eligible_at_exact_125_pct_mfi_boundary` on the upper side.
        """
        screen = self._make_screen()
        self._add_member(screen, age=18, student=True)  # no income stream

        eligibility = self._calc(screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_eligible_at_exact_125_pct_mfi_boundary(self):
        """`<=` boundary: income exactly equal to the 125% MFI cap is eligible."""
        # 1-person cap is $90,500/yr -> use a yearly stream to hit it exactly.
        screen = self._make_screen()
        member = self._add_member(screen, student=True)
        IncomeStream.objects.create(
            screen=screen,
            household_member=member,
            type="wages",
            amount=90_500,
            frequency="yearly",
        )

        eligibility = self._calc(screen).eligible()

        self.assertTrue(eligibility.eligible)

    def test_ineligible_one_dollar_above_125_pct_mfi_boundary(self):
        """`<=` boundary: $1 above the 125% MFI cap is ineligible."""
        screen = self._make_screen()
        member = self._add_member(screen, student=True)
        IncomeStream.objects.create(
            screen=screen,
            household_member=member,
            type="wages",
            amount=90_501,
            frequency="yearly",
        )

        eligibility = self._calc(screen).eligible()

        self.assertFalse(eligibility.eligible)

    # --- Value ---------------------------------------------------------------

    def test_value_is_22500_lump_sum_when_eligible(self):
        """Eligible household returns the published $22,500 lump-sum scholarship."""
        screen = self._make_screen()
        self._add_member(screen, student=True, monthly_wages=2000)

        calc = self._calc(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertEqual(eligibility.value, 22_500)

    def test_value_is_0_when_ineligible(self):
        """Ineligible household reports value 0 (the base class skips value() when not eligible)."""
        screen = self._make_screen()
        self._add_member(screen, student=True, monthly_wages=8000)

        calc = self._calc(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertEqual(eligibility.value, 0)

    def test_value_is_household_level_not_per_member(self):
        """
        Every member returns 0 from member_value; all of the lump-sum
        award is reported at the household level. Confirms the scholarship
        does not multiply across multiple students in the same household.
        """
        screen = self._make_screen(household_size=2)
        self._add_member(screen, student=True, monthly_wages=2000)
        self._add_member(screen, relationship="spouse", age=21, student=True)

        calc = self._calc(screen)
        eligibility = calc.eligible()
        calc.value(eligibility)

        self.assertEqual(eligibility.value, 22_500)
        for member_eligibility in eligibility.eligible_members:
            self.assertEqual(member_eligibility.value, 0)

    # --- MFI table boundaries ------------------------------------------------

    def test_income_limit_table_lookup(self):
        """All 6 published table sizes return the documented 125% MFI value verbatim."""
        for size, expected in WaWsosBas.MFI_125_BY_SIZE.items():
            screen = self._make_screen(household_size=size)
            self.assertEqual(self._calc(screen).income_limit_125(), expected)

    def test_income_limit_extension_above_table(self):
        """
        Sizes above the published table (1-6) extend by the documented
        per-person increment so a 7+ person household is not silently
        denied or crashed.
        """
        screen = self._make_screen(household_size=8)
        expected = WaWsosBas.MFI_125_BY_SIZE[6] + 2 * WaWsosBas.MFI_125_PER_EXTRA_PERSON_ABOVE_TABLE
        self.assertEqual(self._calc(screen).income_limit_125(), expected)

    def test_mfi_table_values_match_spec(self):
        """
        Pin the 2026 published 125% MFI values to the spec table so any
        accidental edit to the lookup is caught here. Verified against
        https://waopportunityscholarship.org/wp-content/uploads/2025/10/
        Baccalaureate-C15-MFI-Chart.pdf
        """
        self.assertEqual(
            WaWsosBas.MFI_125_BY_SIZE,
            {
                1: 90_500,
                2: 118_000,
                3: 146_500,
                4: 174_500,
                5: 202_000,
                6: 230_000,
            },
        )
