from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase, add_income

"""Tests for CO programs affected by the qualifying-relative fix (MFB-722).

Programs covered:
- RTD LiVE: uses is_in_tax_unit() to pick which tax unit to evaluate income against
- Property Credit Rebate: gates on `not member.is_dependent()` — qualifying relatives now excluded
"""


from programs.programs.white_labels.co.rtdlive.calculator import RtdLive
from programs.framework.base import MemberEligibility

# 2024 FPL values (48 contiguous states), mocked for deterministic tests
FPL_2024 = {1: 15060, 2: 20440, 3: 25820, 4: 31200}

DENVER_ZIP = "80204"  # eligible county


class TestRtdLiveQualifyingRelativeImpact(CustomCalculatorTestCase):
    calculator_class = RtdLive
    white_label_code = "co"
    state_code = "CO"
    needs_program_row = False

    def setUp(self):
        """`RtdLive` reads an FPL table off `program.year`, pinned here to FY2024."""
        super().setUp()
        self.program.year.as_dict.return_value = FPL_2024

    def test_eligible_when_household_income_is_low(self):
        """Parents $30k + adult child $0 → combined $30k < 3-person 2.5xFPL ($64,550) → eligible."""
        screen = self.make_screen(zipcode=DENVER_ZIP)
        head = self.add_member(screen, "headOfHousehold", 40)
        add_income(head, 15_000, frequency="yearly")
        spouse = self.add_member(screen, "spouse", 38)
        add_income(spouse, 15_000, frequency="yearly")
        adult_child = self.add_member(screen, "child", 25, student=False)

        self.assertTrue(adult_child.is_in_tax_unit())

        calc = self.make_calculator(screen)
        e = MemberEligibility(adult_child)
        calc.member_eligible(e)

        self.assertTrue(e.eligible)

    def test_ineligible_when_household_income_is_high(self):
        """Post-fix behavior change: adult dependent with high-earning parents loses eligibility.

        Before fix: split into secondary unit, evaluated on own $0 → eligible.
        After fix: joins main unit, evaluated on combined $80k > $64,550 → not eligible.
        """
        screen = self.make_screen(zipcode=DENVER_ZIP)
        head = self.add_member(screen, "headOfHousehold", 40)
        add_income(head, 40_000, frequency="yearly")
        spouse = self.add_member(screen, "spouse", 38)
        add_income(spouse, 40_000, frequency="yearly")
        adult_child = self.add_member(screen, "child", 25, student=False)

        self.assertTrue(adult_child.is_in_tax_unit())

        calc = self.make_calculator(screen)
        e = MemberEligibility(adult_child)
        calc.member_eligible(e)

        self.assertFalse(e.eligible)

    def test_non_dependent_adult_evaluated_on_own_income(self):
        """Adult child earning $10k is above threshold → splits into secondary unit → eligible on own income."""
        screen = self.make_screen(zipcode=DENVER_ZIP)
        head = self.add_member(screen, "headOfHousehold", 40)
        add_income(head, 40_000, frequency="yearly")
        spouse = self.add_member(screen, "spouse", 38)
        add_income(spouse, 40_000, frequency="yearly")
        adult_child = self.add_member(screen, "child", 25, student=False)
        add_income(adult_child, 10_000, frequency="yearly")

        self.assertFalse(adult_child.is_in_tax_unit())

        calc = self.make_calculator(screen)
        e = MemberEligibility(adult_child)
        calc.member_eligible(e)

        self.assertTrue(e.eligible)


class TestPropertyCreditRebateQualifyingRelativeImpact(CustomCalculatorTestCase):
    """CO Property Credit Rebate gates on `not member.is_dependent()`.

    Before fix: low-income adult was NOT a dependent → passed the gate → potentially eligible.
    After fix: low-income adult IS a qualifying relative dependent → excluded from the rebate.
    This is correct IRS behavior — dependents cannot claim their own property credit.
    """

    calculator_class = RtdLive
    white_label_code = "co"
    state_code = "CO"
    needs_program_row = False

    def setUp(self):
        super().setUp()
        self.screen = self.make_screen()
        self.add_member(self.screen, "headOfHousehold", 45)

    def test_qualifying_relative_is_dependent_excluded_from_rebate(self):
        """Adult child with $0 income is now a dependent → excluded by the `not is_dependent()` gate."""
        adult_child = self.add_member(self.screen, "child", 25, student=False)

        self.assertTrue(adult_child.is_dependent())

    def test_non_dependent_adult_passes_rebate_gate(self):
        """Adult child earning above threshold is not a dependent → still passes the gate."""
        adult_child = self.add_member(self.screen, "child", 25, student=False)
        add_income(adult_child, 6_000, frequency="yearly")

        self.assertFalse(adult_child.is_dependent())
