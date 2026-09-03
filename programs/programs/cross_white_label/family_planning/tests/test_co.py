"""
Unit tests for the FamilyPlanningServices (fps) calculator.

Eligibility requirements:
  1. At least one household member has no insurance
  2. Household is NOT Medicaid eligible
  3. Yearly gross household income (excluding cash assistance) below 265% FPL
  4. Member is not pregnant, is 12 or older, and is the head of household or their spouse

Notes:
  - The income limit is sized with `household_size + len(e.eligible_members)`, and
    `eligible_members` holds EVERY member rather than only the eligible ones, so the
    FPL lookup lands at roughly double the true household size. That is a known bug
    tracked separately; the tests below deliberately pin the current behaviour so the
    suite stays green, and are flagged where they do so.
  - The income limit is derived by the real `FederalPoveryLimit.get_limit`, not by a
    copy of it. `get_limit` is pure arithmetic over `as_dict()`, which reads the offline
    `_FPL_DEFAULTS` literal, so it needs neither the database nor the network — an
    unsaved instance is enough.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.models import FederalPoveryLimit
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.cross_white_label.family_planning.co import FamilyPlanningServices
from programs.util import Dependencies, DependencyError
from screener.models import Insurance
from programs.framework.pe_dependencies import member

# Unsaved on purpose: `get_limit` only reads `self.period` and the cached FPL table.
FPL_2025 = FederalPoveryLimit(year="2025", period="2025")


def make_member(age=30, pregnant=False, is_head=True, is_spouse=False, **insurance_flags):
    member = Mock()
    member.age = age
    member.pregnant = pregnant
    member.is_head = Mock(return_value=is_head)
    member.is_spouse = Mock(return_value=is_spouse)
    member.insurance = Insurance(**{"none": False, **insurance_flags})
    return member


def make_data(medicaid_eligible=False):
    if medicaid_eligible is None:
        return {}

    medicaid = Eligibility()
    medicaid.eligible = medicaid_eligible
    return {"co_medicaid": medicaid}


def make_calculator(
    household_size=1,
    household_income=0,
    medicaid_eligible=False,
    members=None,
    missing_dependencies=None,
):
    mock_program = Mock()
    # wraps the real method so call args are still recorded, but the arithmetic is real
    mock_program.year.get_limit = Mock(side_effect=FPL_2025.get_limit)

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.household_members.all.return_value = [make_member(none=True)] if members is None else members

    return FamilyPlanningServices(
        mock_screen,
        mock_program,
        make_data(medicaid_eligible),
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


def eligibility_with_members(count):
    """An `Eligibility` shaped the way `eligible()` hands it to `household_eligible`."""
    e = Eligibility()
    for _ in range(count):
        e.add_member_eligibility(MemberEligibility(make_member()))
    return e


class TestFamilyPlanningServicesClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(FamilyPlanningServices, ProgramCalculator))

    def test_member_amount_is_404(self):
        self.assertEqual(FamilyPlanningServices.member_amount, 404)

    def test_no_household_amount(self):
        self.assertEqual(FamilyPlanningServices.amount, 0)

    def test_min_age_is_12(self):
        self.assertEqual(FamilyPlanningServices.min_age, 12)

    def test_fpl_percent_is_265_percent(self):
        self.assertEqual(FamilyPlanningServices.fpl_percent, 2.65)

    def test_dependencies(self):
        self.assertEqual(
            FamilyPlanningServices.dependencies,
            ["age", "insurance", "income_frequency", "income_amount", "household_size"],
        )


class TestFamilyPlanningServicesInsuranceRequirement(TestCase):
    """At least one member in the household must be uninsured."""

    def _run(self, members):
        calc = make_calculator(members=members)
        e = eligibility_with_members(len(members))
        calc.household_eligible(e)
        return e

    def test_household_with_an_uninsured_member_is_eligible(self):
        self.assertTrue(self._run([make_member(none=True)]).eligible)

    def test_fully_insured_household_is_ineligible(self):
        self.assertFalse(self._run([make_member(private=True)]).eligible)

    def test_one_uninsured_member_is_enough(self):
        members = [make_member(private=True), make_member(none=True)]
        self.assertTrue(self._run(members).eligible)

    def test_dont_know_counts_as_uninsured(self):
        self.assertTrue(self._run([make_member(dont_know=True)]).eligible)

    def test_fully_insured_household_gets_a_fail_message(self):
        e = self._run([make_member(medicaid=True)])
        self.assertGreaterEqual(len(e.fail_messages), 1)


class TestFamilyPlanningServicesMedicaidExclusion(TestCase):
    """Medicaid-eligible households are excluded."""

    def _run(self, medicaid_eligible):
        calc = make_calculator(medicaid_eligible=medicaid_eligible)
        e = eligibility_with_members(1)
        calc.household_eligible(e)
        return e.eligible

    def test_medicaid_eligible_household_is_ineligible(self):
        self.assertFalse(self._run(True))

    def test_non_medicaid_household_is_eligible(self):
        self.assertTrue(self._run(False))

    def test_uncalculated_medicaid_raises_rather_than_reading_as_not_eligible(self):
        """An absent key means "not calculated", which is a different answer from
        "calculated, and not eligible" — so it must not quietly pass the exclusion."""
        with self.assertRaises(DependencyError):
            self._run(None)


class TestFamilyPlanningServicesIncomeEligibility(TestCase):
    """
    Yearly income must be strictly below 265% FPL, excluding cash assistance.

    The FPL size used is `household_size + len(e.eligible_members)`. `eligible_members`
    contains every member, not just the eligible ones, so these boundaries are wider
    than the program's real limits. That is a known bug tracked separately; the
    assertions below pin current behaviour and must be updated when it is fixed.
    """

    def _run(self, household_size, household_income, member_count=1):
        calc = make_calculator(household_size=household_size, household_income=household_income)
        e = eligibility_with_members(member_count)
        calc.household_eligible(e)
        return e.eligible

    def test_income_well_below_the_limit_is_eligible(self):
        self.assertTrue(self._run(1, 10_000))

    def test_income_one_dollar_below_the_limit_is_eligible(self):
        # known bug: size is 1 + 1 = 2, so int(2.65 * 21,150) == 56,047
        self.assertTrue(self._run(1, 56_046))

    def test_income_exactly_at_the_limit_is_ineligible(self):
        # the comparison is strict `<`
        self.assertFalse(self._run(1, 56_047))

    def test_zero_income_is_eligible(self):
        self.assertTrue(self._run(1, 0))

    def test_cash_assistance_and_nurturing_futures_are_excluded_from_income(self):
        # Family planning services is a MAGI-based Medicaid pathway, so none of these count.
        # Both cash-assistance types are excluded: PolicyEngine keeps `tanf` and
        # `financial_assistance` out of adjusted_gross_income, so counting either here would
        # measure a MAGI pathway against non-MAGI income.
        calc = make_calculator(household_income=1_000)
        calc.household_eligible(eligibility_with_members(1))
        calc.screen.calc_gross_income.assert_called_once_with(
            "yearly", ["all"], exclude=["cashAssistance", "cashAssistanceOther", "nurturingFutures"]
        )

    def test_income_limit_is_sized_using_every_member_not_just_eligible_ones(self):
        # Known bug. All three members are counted even though none of the
        # MemberEligibility objects have been evaluated, so a 3-person household is
        # measured against the 6-person FPL: int(2.65 * 43,150) == 114,347.
        calc = make_calculator(household_size=3, household_income=100_000)
        calc.household_eligible(eligibility_with_members(3))
        calc.program.year.get_limit.assert_called_once_with(6)

    def test_ineligible_member_still_widens_the_income_limit(self):
        # Known bug. Once fixed, only genuinely eligible members should count.
        calc = make_calculator(household_size=2, household_income=0)
        e = Eligibility()
        for _ in range(2):
            me = MemberEligibility(make_member())
            me.eligible = False
            e.add_member_eligibility(me)
        calc.household_eligible(e)
        calc.program.year.get_limit.assert_called_once_with(4)


class TestFamilyPlanningServicesMemberEligibility(TestCase):
    """Non-pregnant heads of household or spouses, aged 12 or older."""

    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_head_of_household_is_eligible(self):
        self.assertTrue(self._run(make_member(age=30, is_head=True)))

    def test_spouse_is_eligible(self):
        self.assertTrue(self._run(make_member(age=30, is_head=False, is_spouse=True)))

    def test_other_household_member_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=30, is_head=False, is_spouse=False)))

    def test_pregnant_member_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=30, pregnant=True)))

    def test_age_11_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=11)))

    def test_age_12_is_eligible(self):
        self.assertTrue(self._run(make_member(age=12)))

    def test_age_13_is_eligible(self):
        self.assertTrue(self._run(make_member(age=13)))

    def test_senior_head_of_household_is_eligible(self):
        self.assertTrue(self._run(make_member(age=80)))


class TestFamilyPlanningServicesEligible(TestCase):
    def test_qualifying_household_is_eligible(self):
        members = [make_member(age=30, is_head=True, none=True)]
        calc = make_calculator(household_size=1, household_income=10_000, members=members)
        self.assertTrue(calc.eligible().eligible)

    def test_medicaid_eligible_household_is_ineligible(self):
        members = [make_member(age=30, is_head=True, none=True)]
        calc = make_calculator(household_size=1, household_income=10_000, medicaid_eligible=True, members=members)
        self.assertFalse(calc.eligible().eligible)

    def test_over_income_household_is_ineligible(self):
        members = [make_member(age=30, is_head=True, none=True)]
        calc = make_calculator(household_size=1, household_income=999_999, members=members)
        self.assertFalse(calc.eligible().eligible)

    def test_household_of_only_children_is_ineligible(self):
        members = [make_member(age=8, is_head=False, none=True)]
        calc = make_calculator(household_size=1, household_income=10_000, members=members)
        self.assertFalse(calc.eligible().eligible)

    def test_household_with_no_members_is_ineligible(self):
        calc = make_calculator(household_size=1, household_income=10_000, members=[])
        self.assertFalse(calc.eligible().eligible)


class TestFamilyPlanningServicesValue(TestCase):
    def test_one_qualifying_member_is_worth_404(self):
        members = [make_member(age=30, is_head=True, none=True)]
        calc = make_calculator(household_size=1, household_income=10_000, members=members)
        self.assertEqual(calc.calc().value, 404)

    def test_head_and_spouse_are_each_worth_404(self):
        members = [
            make_member(age=30, is_head=True, none=True),
            make_member(age=30, is_head=False, is_spouse=True, none=True),
        ]
        calc = make_calculator(household_size=2, household_income=10_000, members=members)
        self.assertEqual(calc.calc().value, 808)

    def test_children_add_no_value(self):
        members = [
            make_member(age=30, is_head=True, none=True),
            make_member(age=8, is_head=False, none=True),
        ]
        calc = make_calculator(household_size=2, household_income=10_000, members=members)
        self.assertEqual(calc.calc().value, 404)

    def test_ineligible_household_is_worth_nothing(self):
        members = [make_member(age=30, is_head=True, none=True)]
        calc = make_calculator(household_size=1, household_income=999_999, members=members)
        self.assertEqual(calc.calc().value, 0)


class TestFamilyPlanningServicesCanCalc(TestCase):
    def test_can_calc_with_no_missing_dependencies(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_age(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["age"])).can_calc())

    def test_cannot_calc_without_insurance(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["insurance"])).can_calc())

    def test_can_calc_with_an_unrelated_missing_dependency(self):
        self.assertTrue(make_calculator(missing_dependencies=Dependencies(["zipcode"])).can_calc())

    def test_calc_raises_when_a_dependency_is_missing(self):
        calc = make_calculator(missing_dependencies=Dependencies(["age"]))
        with self.assertRaises(DependencyError):
            calc.calc()
