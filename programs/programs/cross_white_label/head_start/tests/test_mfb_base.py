"""
Unit tests for the MFB Head Start Preschool base (``MfbHeadStart``).

Exercised through a test-only subclass that supplies the values each state sets. State
subclasses test their own values and spec scenarios in their own modules.
"""

from datetime import date
from typing import Optional
from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.cross_white_label.head_start.mfb_base import MfbHeadStart
from programs.programs.cross_white_label.head_start.base import HeadStart
from programs.util import Dependencies

REFERENCE_DATE = date(2026, 10, 15)

# 2026 HHS poverty guidelines, 48 contiguous states and DC.
FPL_2026 = {1: 15_960, 2: 21_640, 3: 27_320, 4: 33_000}


class StateHeadStart(MfbHeadStart):
    program_code = "test_head_start"
    school_eligibility_cutoff_date = (10, 1)
    compulsory_school_age = 6
    weekly_price = 292.30
    program_weeks = 34


class GatedStateHeadStart(StateHeadStart):
    program_code = "test_gated_head_start"
    public_assistance_programs = ("test_snap",)
    gates_on_any = ("test_snap",)


def make_member(age: Optional[int] = 4, birth_year_month: Optional[date] = None, relationship: str = "child") -> Mock:
    member = Mock()
    member.calc_age.return_value = age
    member.birth_year_month = birth_year_month
    member.relationship = relationship
    return member


def make_calculator(
    members: Optional[list] = None,
    income: Optional[dict] = None,
    housing: float = 0,
    base_benefits: tuple = (),
    household_size: int = 3,
    data: Optional[dict] = None,
    cls: type = StateHeadStart,
) -> MfbHeadStart:
    income = income or {}

    def gross_income(frequency: str, types: list) -> float:
        return float(sum(amount for income_type, amount in income.items() if income_type in types))

    screen = Mock()
    screen.household_size = household_size
    screen.get_reference_date.return_value = REFERENCE_DATE
    screen.calc_gross_income.side_effect = gross_income
    screen.calc_expenses.return_value = float(housing)
    screen.has_base_benefit.side_effect = lambda program: program in base_benefits
    screen.household_members.all.return_value = [make_member()] if members is None else members

    program = Mock()
    program.year.get_limit.side_effect = lambda size: FPL_2026[size]

    return cls(screen, program, data or {}, Dependencies())


def run(calculator: MfbHeadStart) -> Eligibility:
    eligibility = calculator.eligible()
    calculator.value(eligibility)
    return eligibility


class TestClassAttributes(SimpleTestCase):
    def test_is_a_custom_calculator(self):
        self.assertTrue(issubclass(MfbHeadStart, ProgramCalculator))

    def test_is_abstract(self):
        self.assertTrue(vars(MfbHeadStart)["_abstract"])

    def test_sits_beside_the_policyengine_base(self):
        self.assertFalse(issubclass(MfbHeadStart, HeadStart))

    def test_reads_every_field_it_uses(self):
        for field in ("age", "relationship", "household_size", "income_type", "expense_type", "expense_amount"):
            self.assertIn(field, MfbHeadStart.dependencies)


class TestAgePreschool(SimpleTestCase):
    def test_three_year_old_is_eligible(self):
        self.assertTrue(run(make_calculator(members=[make_member(age=3)])).eligible)

    def test_five_year_old_is_eligible(self):
        self.assertTrue(run(make_calculator(members=[make_member(age=5)])).eligible)

    def test_compulsory_school_age_is_ineligible(self):
        self.assertFalse(run(make_calculator(members=[make_member(age=6)])).eligible)

    def test_two_year_old_turning_three_by_next_cutoff_is_eligible(self):
        """Born Sept 2024: 2 on 2026-10-15, 3 by the 2027-10-01 cutoff."""
        member = make_member(age=2, birth_year_month=date(2024, 9, 1))
        self.assertTrue(run(make_calculator(members=[member])).eligible)

    def test_two_year_old_turning_three_after_next_cutoff_is_ineligible(self):
        """Born Nov 2024: still 2 on the 2027-10-01 cutoff."""
        member = make_member(age=2, birth_year_month=date(2024, 11, 1))
        self.assertFalse(run(make_calculator(members=[member])).eligible)

    def test_two_year_old_without_birth_month_is_ineligible(self):
        self.assertFalse(run(make_calculator(members=[make_member(age=2)])).eligible)

    def test_unknown_age_is_ineligible(self):
        self.assertFalse(run(make_calculator(members=[make_member(age=None)])).eligible)

    def test_cutoff_later_this_year_is_used_before_it_passes(self):
        calculator = make_calculator()
        calculator.screen.get_reference_date.return_value = date(2026, 9, 15)
        self.assertEqual(calculator._next_cutoff(), date(2026, 10, 1))

    def test_cutoff_rolls_to_next_year_once_passed(self):
        self.assertEqual(make_calculator()._next_cutoff(), date(2027, 10, 1))

    def test_cutoff_on_the_reference_date_is_today(self):
        calculator = make_calculator()
        calculator.screen.get_reference_date.return_value = date(2026, 10, 1)
        self.assertEqual(calculator._next_cutoff(), date(2026, 10, 1))


class TestIncomePovertyLine(SimpleTestCase):
    def test_income_at_the_poverty_line_is_eligible(self):
        self.assertTrue(run(make_calculator(income={"wages": 27_320})).eligible)

    def test_income_one_dollar_over_is_ineligible(self):
        self.assertFalse(run(make_calculator(income={"wages": 27_321})).eligible)

    def test_limit_follows_household_size(self):
        self.assertTrue(run(make_calculator(income={"wages": 33_000}, household_size=4)).eligible)
        self.assertFalse(run(make_calculator(income={"wages": 33_000}, household_size=3)).eligible)

    def test_counts_wages_self_employment_unemployment_and_pension(self):
        income = {"wages": 10_000, "selfEmployment": 10_000, "unemployment": 5_000, "pension": 2_321}
        self.assertFalse(run(make_calculator(income=income)).eligible)

    def test_ignores_income_outside_the_regulations_list(self):
        income = {"wages": 27_000, "veteran": 10_000, "sSDisability": 10_000, "childSupport": 10_000}
        self.assertTrue(run(make_calculator(income=income)).eligible)

    def test_housing_costs_above_30_percent_are_subtracted(self):
        """$30,000 gross, $12,000 housing: $3,000 over 30%, so $27,000 counts."""
        self.assertTrue(run(make_calculator(income={"wages": 30_000}, housing=12_000)).eligible)

    def test_housing_costs_under_30_percent_change_nothing(self):
        self.assertFalse(run(make_calculator(income={"wages": 30_000}, housing=9_000)).eligible)

    def test_housing_expense_types_follow_the_regulation(self):
        calculator = make_calculator(income={"wages": 30_000})
        calculator._countable_income()
        calculator.screen.calc_expenses.assert_called_with(
            "yearly",
            ["rent", "mortgage", "propertyTax", "homeownersInsurance", "heating", "cooling", "otherUtilities"],
        )

    def test_income_failure_reports_the_adjusted_income_and_limit(self):
        eligibility = run(make_calculator(income={"wages": 40_000}))
        self.assertFalse(eligibility.eligible)
        self.assertEqual(len(eligibility.fail_messages), 1)


class TestPublicAssistance(SimpleTestCase):
    over_income = {"wages": 60_000}

    def test_receiving_tanf_ssi_or_snap_qualifies_over_income(self):
        for program in ("tanf", "ssi", "snap"):
            with self.subTest(program=program):
                calculator = make_calculator(income=self.over_income, base_benefits=(program,))
                self.assertTrue(run(calculator).eligible)

    def test_other_benefits_do_not_qualify(self):
        calculator = make_calculator(income=self.over_income, base_benefits=("medicaid", "wic"))
        self.assertFalse(run(calculator).eligible)

    def test_tanf_or_ssi_income_qualifies_over_income(self):
        for income_type in ("cashAssistance", "sSI"):
            with self.subTest(income_type=income_type):
                calculator = make_calculator(income={**self.over_income, income_type: 100})
                self.assertTrue(run(calculator).eligible)

    def test_non_tanf_cash_assistance_does_not_qualify(self):
        calculator = make_calculator(income={**self.over_income, "cashAssistanceOther": 100})
        self.assertFalse(run(calculator).eligible)

    def test_no_program_codes_by_default(self):
        self.assertEqual(MfbHeadStart.public_assistance_programs, ())
        self.assertEqual(StateHeadStart.gates_on_any, ())

    def test_eligible_for_a_state_program_qualifies(self):
        eligible = Eligibility()
        calculator = make_calculator(income=self.over_income, data={"test_snap": eligible}, cls=GatedStateHeadStart)
        self.assertTrue(run(calculator).eligible)

    def test_ineligible_for_a_state_program_does_not_qualify(self):
        ineligible = Eligibility()
        ineligible.eligible = False
        calculator = make_calculator(income=self.over_income, data={"test_snap": ineligible}, cls=GatedStateHeadStart)
        self.assertFalse(run(calculator).eligible)

    def test_an_uncalculated_state_program_does_not_drop_head_start(self):
        calculator = make_calculator(income=self.over_income, base_benefits=("snap",), cls=GatedStateHeadStart)
        self.assertTrue(run(calculator).eligible)


class TestFosterCare(SimpleTestCase):
    over_income = {"wages": 60_000}

    def test_foster_child_qualifies_over_income(self):
        members = [make_member(age=35, relationship="headOfHousehold"), make_member(age=4, relationship="fosterChild")]
        self.assertTrue(run(make_calculator(members=members, income=self.over_income)).eligible)

    def test_only_the_foster_child_is_eligible(self):
        foster = make_member(age=4, relationship="fosterChild")
        sibling = make_member(age=4, relationship="child")
        eligibility = run(make_calculator(members=[foster, sibling], income=self.over_income))
        by_member = {id(me.member): me for me in eligibility.eligible_members}
        self.assertTrue(by_member[id(foster)].eligible)
        self.assertFalse(by_member[id(sibling)].eligible)
        self.assertEqual(eligibility.value, 9_938)

    def test_foster_child_must_still_be_preschool_age(self):
        members = [make_member(age=7, relationship="fosterChild")]
        self.assertFalse(run(make_calculator(members=members, income=self.over_income)).eligible)


class TestValue(SimpleTestCase):
    def test_value_is_weekly_price_times_program_weeks(self):
        """$292.30 x 34 = $9,938.20, rounded."""
        self.assertEqual(run(make_calculator()).value, 9_938)

    def test_value_is_per_eligible_child(self):
        members = [make_member(age=35, relationship="headOfHousehold"), make_member(age=3), make_member(age=5)]
        self.assertEqual(run(make_calculator(members=members)).value, 2 * 9_938)

    def test_ineligible_household_has_no_value(self):
        self.assertEqual(run(make_calculator(income={"wages": 60_000})).value, 0)
