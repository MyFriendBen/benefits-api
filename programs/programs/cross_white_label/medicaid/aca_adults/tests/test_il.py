"""Illinois ACA Adults (il_aca_adults) — first tests.

The leftover Medicaid category: adults FamilyCare and Moms & Babies do not reach. That
makes it the codebase's clearest case of a dependency on another program's eligibility
being the rule itself rather than a proxy for one — "not eligible for either sibling" has
no restatement in terms of this household's own facts, because the siblings' rules *are*
the facts it turns on.

It gates on three programs, which is the most of any calculator, and had no test coverage
at all. Households are hand-rolled on Mock screens; `CustomCalculatorTestCase` would
replace the boilerplate and is still unmerged.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.cross_white_label.medicaid.aca_adults.il import AcaAdults
from programs.util import Dependencies, DependencyError, UpstreamAbsentError

# Comfortably under 138% FPL for the household sizes used here.
LOW_INCOME = 10_000
FPL_ONE_PERSON = 15_060


def make_member(age=30, relationship="headOfHousehold", pregnant=False, medicaid=False):
    member = Mock()
    member.age = age
    member.relationship = relationship
    member.pregnant = pregnant
    member.has_insurance.side_effect = lambda kind: medicaid and kind == "medicaid"
    return member


def make_data(medicaid=True, family_care=False, moms_and_babies=False):
    """The eligibility loop's `data`. `None` for any of the three leaves the key absent,
    which is what the strict gates raise on."""
    data = {}
    for code, verdict in (
        ("il_medicaid", medicaid),
        ("il_family_care", family_care),
        ("il_moms_and_babies", moms_and_babies),
    ):
        if verdict is None:
            continue
        eligibility = Eligibility()
        eligibility.eligible = verdict
        data[code] = eligibility

    return data


def make_calculator(
    medicaid=True,
    family_care=False,
    moms_and_babies=False,
    income=LOW_INCOME,
    household_size=1,
    members=None,
    pregnant_count=0,
    children=0,
    missing_dependencies=None,
):
    screen = Mock()
    screen.household_size = household_size
    screen.calc_gross_income.return_value = income
    screen.household_members.filter.return_value.count.return_value = pregnant_count
    screen.num_children.return_value = children
    screen.household_members.all.return_value = [make_member()] if members is None else members

    program = Mock()
    program.year.get_limit.side_effect = lambda size: FPL_ONE_PERSON * size

    return AcaAdults(
        screen,
        program,
        make_data(medicaid, family_care, moms_and_babies),
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class TestRegistration(TestCase):
    def test_is_a_program_calculator(self):
        self.assertTrue(issubclass(AcaAdults, ProgramCalculator))

    def test_program_code(self):
        self.assertEqual(AcaAdults.program_code, "il_aca_adults")

    def test_declares_all_three_gates(self):
        self.assertEqual(AcaAdults.gates_on, ("il_medicaid", "il_family_care", "il_moms_and_babies"))


class TestItIsTheLeftoverCategory(TestCase):
    """One positive gate and two exclusions. All three are required, so the household has
    to be Medicaid-eligible *and* fall outside both sibling programs."""

    def _eligible(self, **kwargs):
        e = Eligibility()
        make_calculator(**kwargs).household_eligible(e)
        return e.eligible

    def test_medicaid_eligible_and_outside_both_siblings_is_eligible(self):
        self.assertTrue(self._eligible())

    def test_not_medicaid_eligible_is_not_eligible(self):
        self.assertFalse(self._eligible(medicaid=False))

    def test_family_care_eligible_is_excluded(self):
        self.assertFalse(self._eligible(family_care=True))

    def test_moms_and_babies_eligible_is_excluded(self):
        self.assertFalse(self._eligible(moms_and_babies=True))

    def test_eligible_for_both_siblings_is_excluded(self):
        self.assertFalse(self._eligible(family_care=True, moms_and_babies=True))


class TestNoneOfTheThreeGatesGuesses(TestCase):
    """An exclusion is the dangerous direction: reading an absent upstream as "not
    eligible for the thing that disqualifies them" would offer the program to someone who
    should have been screened out. All three use the raising accessor."""

    def _raise_for(self, **kwargs):
        with self.assertRaises(UpstreamAbsentError) as caught:
            make_calculator(**kwargs).household_eligible(Eligibility())
        return caught.exception.program_code

    def test_uncalculated_medicaid_raises(self):
        self.assertEqual(self._raise_for(medicaid=None), "il_medicaid")

    def test_uncalculated_family_care_raises(self):
        self.assertEqual(self._raise_for(family_care=None), "il_family_care")

    def test_uncalculated_moms_and_babies_raises(self):
        self.assertEqual(self._raise_for(moms_and_babies=None), "il_moms_and_babies")

    def test_an_absent_exclusion_is_not_read_permissively(self):
        """The failure this prevents: treating "Moms & Babies was not calculated" as "not
        eligible for Moms & Babies" and offering ACA Adults to a household that should
        have been excluded."""
        with self.assertRaises(DependencyError):
            make_calculator(moms_and_babies=None).household_eligible(Eligibility())


class TestIncomeAgainst138Fpl(TestCase):
    def _eligible(self, income, **kwargs):
        e = Eligibility()
        make_calculator(income=income, **kwargs).household_eligible(e)
        return e.eligible

    def test_income_at_the_limit_is_eligible(self):
        self.assertTrue(self._eligible(int(FPL_ONE_PERSON * 1.38)))

    def test_income_above_the_limit_is_not(self):
        self.assertFalse(self._eligible(int(FPL_ONE_PERSON * 1.38) + 1))

    def test_a_pregnant_member_raises_the_limit_by_one_household_size(self):
        """The shared IL mixin counts a pregnant member as two people, so the same income
        can pass at a size it would fail at otherwise."""
        income = int(FPL_ONE_PERSON * 2 * 1.38)

        self.assertFalse(self._eligible(income, household_size=1, pregnant_count=0))
        self.assertTrue(self._eligible(income, household_size=1, pregnant_count=1))


class TestMemberConditions(TestCase):
    def _member_eligible(self, member, children=0):
        e = MemberEligibility(member)
        make_calculator(children=children).member_eligible(e)
        return e.eligible

    def test_an_adult_in_band_is_eligible(self):
        self.assertTrue(self._member_eligible(make_member(age=30)))

    def test_below_nineteen_is_not(self):
        self.assertFalse(self._member_eligible(make_member(age=18)))

    def test_the_lower_and_upper_bounds_are_eligible(self):
        self.assertTrue(self._member_eligible(make_member(age=19)))
        self.assertTrue(self._member_eligible(make_member(age=64)))

    def test_sixty_five_is_not(self):
        self.assertFalse(self._member_eligible(make_member(age=65)))

    def test_a_pregnant_member_is_not(self):
        """Pregnancy routes to Moms & Babies, so ACA Adults excludes it at member scope as
        well as through the sibling gate."""
        self.assertFalse(self._member_eligible(make_member(pregnant=True)))

    def test_a_caretaker_of_children_is_not(self):
        """Caretakers route to FamilyCare."""
        self.assertFalse(self._member_eligible(make_member(relationship="parent"), children=1))

    def test_a_caretaker_with_no_children_is_eligible(self):
        self.assertTrue(self._member_eligible(make_member(relationship="parent"), children=0))

    def test_a_non_caretaker_in_a_household_with_children_is_eligible(self):
        self.assertTrue(self._member_eligible(make_member(relationship="child"), children=1))

    def test_a_member_already_on_medicaid_is_not(self):
        self.assertFalse(self._member_eligible(make_member(medicaid=True)))


class TestCanCalc(TestCase):
    def test_can_calc_with_nothing_missing(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_its_own_fields(self):
        for field in AcaAdults.dependencies:
            with self.subTest(field=field):
                self.assertFalse(make_calculator(missing_dependencies=Dependencies([field])).can_calc())

    def test_cannot_calc_without_a_field_only_il_medicaid_reads(self):
        """`household_assets` is PolicyEngine Medicaid's, reached through `pe_inputs`. It
        was not declared here before, so ACA Adults was calculable on screens where
        `il_medicaid` was not and all three gates raised."""
        self.assertNotIn("household_assets", AcaAdults.dependencies)
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["household_assets"])).can_calc())

    def test_can_calc_with_a_field_no_gate_reads(self):
        self.assertTrue(make_calculator(missing_dependencies=Dependencies(["expense_amount"])).can_calc())
