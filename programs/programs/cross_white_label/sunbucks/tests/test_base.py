"""
Unit tests for the SUN Bucks base (``SunBucks``).

Exercised through test-only subclasses that supply the values each state sets. The base spec has
no scenarios of its own, so each rule in its sections 3, 4 and 7 gets a test here; NJ's spec
scenarios run end to end in ``test_nj.py``.
"""

from datetime import date
from typing import Optional
from unittest.mock import Mock

from django.test import SimpleTestCase

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility, ProgramCalculator
from programs.framework.pe_dependencies.receipt import TANF_INCOME_TYPE
from programs.programs.cross_white_label.sunbucks.base import FOSTER_CHILD, SNAP, TANF, SunBucks
from programs.util import Dependencies

# 2026 HHS poverty guidelines at 100%, 48 contiguous states and DC.
FPL_2026 = {1: 15_960, 2: 21_640, 3: 27_320, 4: 33_000}


class StateSunBucks(SunBucks):
    program_code = "test_sunbucks"
    min_school_age = 5
    max_school_age = 17


class WindowedStateSunBucks(StateSunBucks):
    program_code = "test_windowed_sunbucks"
    school_age_window = (date(2025, 7, 1), date(2026, 8, 31))


class AutoEnrollingStateSunBucks(StateSunBucks):
    program_code = "test_auto_enrolling_sunbucks"
    enrolled_automatically = (SNAP, TANF, FOSTER_CHILD)


def make_member(age: Optional[int] = 8, relationship: str = "child", birth_year_month: Optional[date] = None) -> Mock:
    member = Mock()
    member.calc_age.return_value = age
    member.relationship = relationship
    member.birth_year_month = birth_year_month
    return member


def make_calculator(
    members: Optional[list] = None,
    income: float = 0,
    cash_assistance: float = 0,
    base_benefits: tuple = (),
    household_size: int = 3,
    cls: type = StateSunBucks,
) -> SunBucks:
    def gross_income(frequency: str, types: list) -> float:
        return float(cash_assistance if types == [TANF_INCOME_TYPE] else income)

    screen = Mock()
    screen.household_size = household_size
    screen.calc_gross_income.side_effect = gross_income
    screen.has_base_benefit.side_effect = lambda program: program in base_benefits
    screen.household_members.all.return_value = [make_member()] if members is None else members

    program = Mock()
    program.year.get_limit.side_effect = lambda size: FPL_2026[size]

    return cls(screen, program, {}, Dependencies())


def run(calculator: SunBucks) -> Eligibility:
    eligibility = calculator.eligible()
    calculator.value(eligibility)
    return eligibility


class TestClassAttributes(SimpleTestCase):
    def test_base_is_abstract_and_state_is_not(self):
        self.assertTrue(SunBucks._abstract)
        self.assertFalse(StateSunBucks._abstract)
        self.assertTrue(issubclass(SunBucks, ProgramCalculator))

    def test_federal_constants(self):
        self.assertEqual(SunBucks.income_limit_percent, 185)
        self.assertEqual(SunBucks.member_amount, 120)

    def test_base_enrolls_snap_automatically_and_nothing_else(self):
        self.assertEqual(SunBucks.enrolled_automatically, (SNAP,))

    def test_dependencies_cover_what_the_calculator_reads(self):
        for field in ("age", "relationship", "household_size", "income_amount", "income_frequency", "income_type"):
            self.assertIn(field, SunBucks.dependencies)


class TestSchoolAge(SimpleTestCase):
    """`school_aged`: calc_age within the state's compulsory ages, inclusive."""

    def eligible_for_age(self, age: Optional[int]) -> bool:
        calculator = make_calculator(members=[make_member(age=age)], base_benefits=("nslp",))
        return run(calculator).eligible_members[0].eligible

    def test_min_age_is_eligible(self):
        self.assertTrue(self.eligible_for_age(5))

    def test_max_age_is_eligible(self):
        self.assertTrue(self.eligible_for_age(17))

    def test_below_min_age_is_ineligible(self):
        self.assertFalse(self.eligible_for_age(4))

    def test_above_max_age_is_ineligible(self):
        self.assertFalse(self.eligible_for_age(18))

    def test_unknown_age_is_ineligible(self):
        self.assertFalse(self.eligible_for_age(None))

    def test_household_with_no_school_age_child_is_ineligible_even_on_school_meals(self):
        calculator = make_calculator(
            members=[make_member(age=40, relationship="headOfHousehold")], base_benefits=("nslp",)
        )
        self.assertFalse(run(calculator).eligible)


class TestSchoolAgeWindow(SimpleTestCase):
    """A state's window: school age at some point between its first and last day."""

    def eligible_born(self, birth_year_month: Optional[date], age: Optional[int] = 30) -> bool:
        member = make_member(age=age, birth_year_month=birth_year_month)
        calculator = make_calculator(members=[member], base_benefits=("nslp",), cls=WindowedStateSunBucks)
        return run(calculator).eligible_members[0].eligible

    def test_reaching_min_age_on_the_last_day_is_eligible(self):
        self.assertTrue(self.eligible_born(date(2021, 8, 1)))

    def test_reaching_min_age_after_the_last_day_is_ineligible(self):
        self.assertFalse(self.eligible_born(date(2021, 9, 1)))

    def test_max_age_on_the_first_day_is_eligible(self):
        self.assertTrue(self.eligible_born(date(2007, 8, 1)))

    def test_past_max_age_on_the_first_day_is_ineligible(self):
        self.assertFalse(self.eligible_born(date(2007, 7, 1)))

    def test_no_birth_month_falls_back_to_age_today(self):
        self.assertTrue(self.eligible_born(None, age=10))
        self.assertFalse(self.eligible_born(None, age=18))


class TestEnrolledAutomatically(SimpleTestCase):
    """A child the state enrolls with no application is not shown the program."""

    def test_snap_household_is_hidden(self):
        e = run(make_calculator(base_benefits=("snap",)))
        self.assertFalse(e.eligible)
        self.assertIn(messages.must_not_have_benefit("SNAP"), e.fail_messages)
        self.assertEqual(e.value, 0)

    def test_snap_hides_a_household_that_also_passes_another_route(self):
        self.assertFalse(run(make_calculator(income=0, base_benefits=("snap", "nslp"))).eligible)

    def test_base_does_not_hide_tanf(self):
        self.assertTrue(run(make_calculator(income=500_000, base_benefits=("tanf",))).eligible)

    def test_base_does_not_hide_a_foster_child(self):
        members = [make_member(age=9, relationship="fosterChild")]
        self.assertTrue(run(make_calculator(members=members, income=500_000)).eligible)

    def test_school_meals_and_head_start_never_hide(self):
        for program in ("nslp", "head_start"):
            calculator = make_calculator(base_benefits=(program,), cls=AutoEnrollingStateSunBucks)
            self.assertTrue(run(calculator).eligible, program)

    def test_state_can_hide_tanf_reported_as_a_benefit(self):
        e = run(make_calculator(base_benefits=("tanf",), cls=AutoEnrollingStateSunBucks))
        self.assertFalse(e.eligible)
        self.assertIn(messages.must_not_have_benefit("TANF"), e.fail_messages)

    def test_state_can_hide_tanf_reported_as_cash_assistance_income(self):
        calculator = make_calculator(cash_assistance=3_000, cls=AutoEnrollingStateSunBucks)
        self.assertFalse(run(calculator).eligible)

    def test_state_can_hide_a_foster_child_but_not_their_siblings(self):
        members = [make_member(age=9, relationship="fosterChild"), make_member(age=10, relationship="child")]
        e = run(make_calculator(members=members, income=0, cls=AutoEnrollingStateSunBucks))
        self.assertTrue(e.eligible)
        self.assertEqual([m.eligible for m in e.eligible_members], [False, True])

    def test_household_with_only_a_hidden_foster_child_is_ineligible(self):
        members = [make_member(age=9, relationship="fosterChild")]
        self.assertFalse(run(make_calculator(members=members, income=0, cls=AutoEnrollingStateSunBucks)).eligible)


class TestCategoricalAndSchoolMeals(SimpleTestCase):
    """`tanf_household`, `head_start_child` and `school_meal_certified` bypass the income test."""

    def assert_presumed(self, cash_assistance: float = 0, base_benefits: tuple = ()) -> None:
        calculator = make_calculator(income=500_000, cash_assistance=cash_assistance, base_benefits=base_benefits)
        e = run(calculator)
        self.assertTrue(e.eligible)
        self.assertIn(messages.presumed_eligibility(), e.pass_messages)

    def test_tanf(self):
        self.assert_presumed(base_benefits=("tanf",))

    def test_tanf_reported_as_cash_assistance_income(self):
        self.assert_presumed(cash_assistance=3_000)

    def test_head_start(self):
        self.assert_presumed(base_benefits=("head_start",))

    def test_school_meals(self):
        self.assert_presumed(base_benefits=("nslp",))

    def test_unrelated_benefit_does_not_bypass_income(self):
        calculator = make_calculator(income=500_000, base_benefits=("medicaid",))
        self.assertFalse(run(calculator).eligible)

    def test_every_school_age_child_in_a_receiving_household_qualifies(self):
        members = [
            make_member(age=6),
            make_member(age=12),
            make_member(age=2),
            make_member(age=35, relationship="headOfHousehold"),
        ]
        e = run(make_calculator(members=members, base_benefits=("nslp",)))
        self.assertEqual([m.eligible for m in e.eligible_members], [True, True, False, False])


class TestIncomeApplication(SimpleTestCase):
    """`income_limit`: gross yearly income at or below 185% of poverty, rounded up."""

    def test_limit_rounds_up_to_the_whole_dollar(self):
        # 1.85 * 15,960 = 29,526; 1.85 * 21,640 = 40,034; 1.85 * 27,320 = 50,542; 1.85 * 33,000 = 61,050
        for size, expected in {1: 29_526, 2: 40_034, 3: 50_542, 4: 61_050}.items():
            self.assertEqual(make_calculator(household_size=size)._income_limit(), expected)

    def test_limit_rounds_a_fraction_up(self):
        calculator = make_calculator()
        calculator.program.year.get_limit.side_effect = lambda size: 15_961
        self.assertEqual(calculator._income_limit(), 29_528)  # 29,527.85

    def test_income_at_the_limit_is_eligible(self):
        e = run(make_calculator(income=50_542))
        self.assertTrue(e.eligible)
        self.assertIn(messages.income(50_542, 50_542), e.pass_messages)

    def test_income_one_dollar_over_is_ineligible(self):
        e = run(make_calculator(income=50_543))
        self.assertFalse(e.eligible)
        self.assertIn(messages.income(50_543, 50_542), e.fail_messages)

    def test_limit_follows_household_size(self):
        self.assertTrue(run(make_calculator(income=40_034, household_size=2)).eligible)
        self.assertFalse(run(make_calculator(income=40_035, household_size=2)).eligible)

    def test_income_counts_every_stream_yearly(self):
        calculator = make_calculator(income=1_000)
        run(calculator)
        calculator.screen.calc_gross_income.assert_called_with("yearly", ["all"])

    def test_zero_income_is_eligible(self):
        self.assertTrue(run(make_calculator(income=0)).eligible)


class TestFosterChild(SimpleTestCase):
    """`foster_child`: the foster child's own eligibility, over income and without siblings."""

    def test_foster_child_qualifies_over_income(self):
        members = [make_member(age=9, relationship="fosterChild")]
        self.assertTrue(run(make_calculator(members=members, income=500_000)).eligible)

    def test_siblings_of_a_foster_child_do_not(self):
        members = [make_member(age=9, relationship="fosterChild"), make_member(age=10, relationship="child")]
        e = run(make_calculator(members=members, income=500_000))
        self.assertTrue(e.eligible)
        self.assertEqual([m.eligible for m in e.eligible_members], [True, False])

    def test_foster_child_outside_school_age_is_ineligible(self):
        members = [make_member(age=3, relationship="fosterChild")]
        self.assertFalse(run(make_calculator(members=members, income=500_000)).eligible)

    def test_under_income_siblings_all_qualify(self):
        members = [make_member(age=9, relationship="fosterChild"), make_member(age=10, relationship="child")]
        e = run(make_calculator(members=members, income=10_000))
        self.assertEqual([m.eligible for m in e.eligible_members], [True, True])


class TestValue(SimpleTestCase):
    """Section 7: $40 a month for three months, $120 per eligible child."""

    def test_value_is_120_per_eligible_child(self):
        members = [make_member(age=6), make_member(age=11), make_member(age=2)]
        e = run(make_calculator(members=members, base_benefits=("nslp",)))
        self.assertEqual([m.value for m in e.eligible_members], [120, 120, 0])
        self.assertEqual(e.value, 240)

    def test_ineligible_household_has_no_value(self):
        e = run(make_calculator(income=500_000))
        self.assertEqual(e.value, 0)

    def test_value_is_positive_for_an_eligible_household(self):
        # SUN and zero are filtered out of results, so an eligible household must never land on zero.
        self.assertGreater(run(make_calculator(income=0)).value, 0)
