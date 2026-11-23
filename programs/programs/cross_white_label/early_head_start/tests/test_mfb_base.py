"""
Unit tests for the MFB Early Head Start base (``MfbEarlyHeadStart``).

Exercised through test-only subclasses that supply the values each state sets. State
subclasses test their own values and spec scenarios in their own modules. The base spec
(``programs/cross_white_label/early_head_start/base/early_head_start_base_spec.md`` in
program-ops) has no scenarios of its own, so these cover each base rule directly.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from unittest.mock import Mock

from django.test import SimpleTestCase

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
from programs.programs.cross_white_label.early_head_start.mfb_base import MfbEarlyHeadStart
from programs.programs.cross_white_label.head_start.eligibility import HeadStartEligibility
from programs.programs.testing_fixtures.custom_calculator import eligible_result, ineligible_result
from programs.util import Dependencies

REFERENCE_DATE = date(2026, 10, 15)

# 2026 HHS poverty guidelines, 48 contiguous states and DC.
FPL_2026 = {1: 15_960, 2: 21_640, 3: 27_320, 4: 33_000}

INFANT, TODDLER, OLDEST = 300, 200, 100


class StateEarlyHeadStart(MfbEarlyHeadStart):
    """Three bands, priced so each value is easy to read: 300, 200 or 100 a week for 10 weeks."""

    program_code = "test_early_head_start"
    weekly_prices = ((0, Decimal(INFANT)), (18, Decimal(TODDLER)), (30, Decimal(OLDEST)))
    program_weeks = 10


class OneBandEarlyHeadStart(MfbEarlyHeadStart):
    program_code = "test_one_band_early_head_start"
    weekly_prices = ((0, Decimal("100.05")),)
    program_weeks = 10


class GatedStateEarlyHeadStart(StateEarlyHeadStart):
    program_code = "test_gated_early_head_start"
    gates_on_any = ("test_ssi",)


def born_months_ago(months: int) -> date:
    total = REFERENCE_DATE.year * 12 + REFERENCE_DATE.month - 1 - months
    return date(total // 12, total % 12 + 1, 1)


def make_member(
    months: Optional[int] = 10,
    age: Optional[int] = None,
    relationship: str = "child",
    pregnant: Optional[bool] = False,
) -> Mock:
    """A member `months` old, or of whole-year `age` with no birth month when `months` is None."""
    member = Mock()
    if months is None:
        member.birth_year_month = None
        member.calc_age.return_value = age
    else:
        member.birth_year_month = born_months_ago(months)
        member.calc_age.return_value = months // 12
    member.relationship = relationship
    member.pregnant = pregnant
    return member


def pregnant_adult(relationship: str = "headOfHousehold") -> Mock:
    return make_member(months=26 * 12, relationship=relationship, pregnant=True)


def make_calculator(
    members: Optional[list] = None,
    income: Optional[dict] = None,
    housing: float = 0,
    base_benefits: tuple = (),
    household_size: int = 2,
    data: Optional[dict] = None,
    cls: type = StateEarlyHeadStart,
) -> MfbEarlyHeadStart:
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


def run(calculator: MfbEarlyHeadStart) -> Eligibility:
    eligibility = calculator.eligible()
    calculator.value(eligibility)
    return eligibility


class TestClassAttributes(SimpleTestCase):
    def test_is_a_custom_calculator(self):
        self.assertTrue(issubclass(MfbEarlyHeadStart, ProgramCalculator))

    def test_is_abstract(self):
        self.assertTrue(vars(MfbEarlyHeadStart)["_abstract"])

    def test_sits_beside_the_policyengine_base(self):
        self.assertFalse(issubclass(MfbEarlyHeadStart, EarlyHeadStart))

    def test_shares_head_starts_household_rules(self):
        self.assertTrue(issubclass(MfbEarlyHeadStart, HeadStartEligibility))

    def test_reads_every_field_it_uses(self):
        for field in (
            "age",
            "relationship",
            "pregnant",
            "household_size",
            "income_type",
            "income_amount",
            "income_frequency",
            "expense_type",
            "expense_amount",
            "expense_frequency",
        ):
            self.assertIn(field, MfbEarlyHeadStart.dependencies)


class TestAgeUnderThree(SimpleTestCase):
    def eligible_members(self, member: Mock) -> list:
        eligibility = run(make_calculator(members=[member], income={"wages": 10_000}))
        return [m.member for m in eligibility.eligible_members if m.eligible]

    def test_newborn_is_eligible(self):
        member = make_member(months=0)
        self.assertEqual(self.eligible_members(member), [member])

    def test_35_months_is_eligible(self):
        member = make_member(months=35)
        self.assertEqual(self.eligible_members(member), [member])

    def test_36_months_is_ineligible(self):
        self.assertEqual(self.eligible_members(make_member(months=36)), [])

    def test_age_without_birth_month_is_read_in_years(self):
        two = make_member(months=None, age=2)
        self.assertEqual(self.eligible_members(two), [two])
        self.assertEqual(self.eligible_members(make_member(months=None, age=3)), [])

    def test_unknown_age_is_ineligible(self):
        self.assertEqual(self.eligible_members(make_member(months=None, age=None)), [])


class TestPregnant(SimpleTestCase):
    def test_pregnant_woman_is_eligible(self):
        woman = pregnant_adult()
        eligibility = run(make_calculator(members=[woman], income={"wages": 10_000}, household_size=1))

        self.assertTrue(eligibility.eligible)

    def test_adult_who_is_not_pregnant_is_ineligible(self):
        adult = make_member(months=26 * 12)
        eligibility = run(make_calculator(members=[adult], income={"wages": 10_000}, household_size=1))

        self.assertFalse(eligibility.eligible)

    def test_unanswered_pregnancy_is_not_pregnant(self):
        adult = make_member(months=26 * 12, pregnant=None)
        eligibility = run(make_calculator(members=[adult], income={"wages": 10_000}, household_size=1))

        self.assertFalse(eligibility.eligible)


class TestIncomePovertyLine(SimpleTestCase):
    def test_income_at_the_poverty_line_is_eligible(self):
        eligibility = run(make_calculator(income={"wages": 21_640}))

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.pass_messages, [messages.income(21_640, 21_640)])

    def test_income_one_dollar_over_is_ineligible(self):
        eligibility = run(make_calculator(income={"wages": 21_641}))

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.fail_messages, [messages.income(21_641, 21_640)])

    def test_housing_costs_above_30_percent_are_subtracted(self):
        """$24,000 - ($9,600 - 0.30 x $24,000) = $21,600."""
        eligibility = run(make_calculator(income={"wages": 24_000}, housing=9_600))

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.pass_messages, [messages.income(21_600, 21_640)])

    def test_counts_only_the_regulations_income(self):
        eligibility = run(make_calculator(income={"wages": 10_000, "childSupport": 50_000}))

        self.assertTrue(eligibility.eligible)


class TestPublicAssistance(SimpleTestCase):
    over_income = {"wages": 40_000}

    def test_receiving_tanf_ssi_or_snap_qualifies_over_income(self):
        for program in ("tanf", "ssi", "snap"):
            with self.subTest(program=program):
                eligibility = run(make_calculator(income=self.over_income, base_benefits=(program,)))

                self.assertTrue(eligibility.eligible)
                self.assertEqual(eligibility.pass_messages, [messages.presumed_eligibility()])

    def test_other_benefits_do_not_qualify(self):
        eligibility = run(make_calculator(income=self.over_income, base_benefits=("wic",)))

        self.assertFalse(eligibility.eligible)

    def test_tanf_or_ssi_income_qualifies_over_income(self):
        for income_type in ("cashAssistance", "sSI"):
            with self.subTest(income_type=income_type):
                eligibility = run(make_calculator(income={**self.over_income, income_type: 3_000}))

                self.assertTrue(eligibility.eligible)

    def test_pregnant_woman_qualifies_through_public_assistance(self):
        calculator = make_calculator(
            members=[pregnant_adult()], income=self.over_income, base_benefits=("snap",), household_size=1
        )

        self.assertTrue(run(calculator).eligible)

    def test_eligible_for_the_states_program_qualifies(self):
        calculator = make_calculator(
            income=self.over_income, data={"test_ssi": eligible_result()}, cls=GatedStateEarlyHeadStart
        )

        self.assertTrue(run(calculator).eligible)

    def test_ineligible_for_the_states_program_does_not_qualify(self):
        calculator = make_calculator(
            income=self.over_income, data={"test_ssi": ineligible_result()}, cls=GatedStateEarlyHeadStart
        )

        self.assertFalse(run(calculator).eligible)

    def test_an_uncalculated_state_program_does_not_drop_early_head_start(self):
        calculator = make_calculator(income=self.over_income, cls=GatedStateEarlyHeadStart)

        self.assertFalse(run(calculator).eligible)


class TestFosterCare(SimpleTestCase):
    over_income = {"wages": 90_000}

    def test_foster_child_qualifies_over_income(self):
        child = make_member(months=24, relationship="fosterChild")
        eligibility = run(make_calculator(members=[child], income=self.over_income))

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.value, TODDLER * 10)

    def test_only_the_foster_child_is_eligible(self):
        foster = make_member(months=24, relationship="fosterChild")
        sibling = make_member(months=10, relationship="child")
        eligibility = run(make_calculator(members=[foster, sibling], income=self.over_income, household_size=3))

        self.assertEqual([m.member for m in eligibility.eligible_members if m.eligible], [foster])

    def test_a_related_child_does_not_qualify(self):
        grandchild = make_member(months=24, relationship="grandChild")
        eligibility = run(make_calculator(members=[grandchild], income=self.over_income))

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.fail_messages, [messages.income(90_000, 21_640)])

    def test_a_pregnant_foster_teen_does_not_qualify_through_foster_care(self):
        """The foster care route is the child's, so it never reaches a pregnant woman."""
        teen = make_member(months=16 * 12, relationship="fosterChild", pregnant=True)
        eligibility = run(make_calculator(members=[teen], income=self.over_income))

        self.assertFalse(eligibility.eligible)


class TestValue(SimpleTestCase):
    def value_at(self, months: Optional[int], age: Optional[int] = None, cls: type = StateEarlyHeadStart) -> int:
        member = make_member(months=months, age=age)
        return run(make_calculator(members=[member], income={"wages": 10_000}, cls=cls)).value

    def test_each_band_is_its_weekly_price_times_program_weeks(self):
        for months, weekly in ((0, INFANT), (17, INFANT), (18, TODDLER), (29, TODDLER), (30, OLDEST), (35, OLDEST)):
            with self.subTest(months=months):
                self.assertEqual(self.value_at(months), weekly * 10)

    def test_age_without_birth_month_starts_at_that_years_first_month(self):
        for age, weekly in ((0, INFANT), (1, INFANT), (2, TODDLER)):
            with self.subTest(age=age):
                self.assertEqual(self.value_at(None, age=age), weekly * 10)

    def test_a_pregnant_woman_is_one_infant_slot(self):
        eligibility = run(make_calculator(members=[pregnant_adult()], income={"wages": 10_000}, household_size=1))

        self.assertEqual(eligibility.value, INFANT * 10)

    def test_value_is_per_eligible_member(self):
        members = [pregnant_adult(), make_member(months=10), make_member(months=24), make_member(months=7 * 12)]
        eligibility = run(make_calculator(members=members, income={"wages": 10_000}, household_size=4))

        self.assertEqual(eligibility.value, (INFANT + INFANT + TODDLER) * 10)

    def test_one_band_state_prices_every_age_alike_and_rounds_half_up(self):
        """100.05 x 10 = 1,000.50, which rounds half-up to 1,001."""
        for months in (0, 20, 35):
            with self.subTest(months=months):
                self.assertEqual(self.value_at(months, cls=OneBandEarlyHeadStart), 1_001)

    def test_ineligible_household_has_no_value(self):
        eligibility = run(make_calculator(income={"wages": 40_000}))

        self.assertEqual(eligibility.value, 0)
