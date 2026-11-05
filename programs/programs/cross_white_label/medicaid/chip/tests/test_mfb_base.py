"""
Unit tests for the MFB CHIP base (``MfbChip``, ``MfbChipFcep``, ``MfbChipCommon``).

Exercised through test-only subclasses that supply the values a state sets. The base spec
(program-ops ``programs/cross_white_label/medicaid/chip/base/chip_base_spec.md``) has no
scenarios of its own, so each rule in its sections 4 and 7 gets a test here; NJ's spec
scenarios run end to end in ``test_nj.py``.

Limits are chosen so the boundaries are easy to read: a family of 3 has a 27,320 poverty
line, so each percentage point is 273.20 a year.
"""

from typing import Optional
from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.medicaid.chip.mfb_base import (
    MAGI_EXCLUDED_INCOME_TYPES,
    MfbChip,
    MfbChipCommon,
    MfbChipFcep,
)
from programs.util import Dependencies, DependencyError

# 2026 HHS poverty guidelines at 100%, 48 contiguous states and DC.
FPL_2026 = {1: 15_960, 2: 21_640, 3: 27_320, 4: 33_000, 5: 38_680, 6: 44_360}


class StateChip(MfbChip):
    program_code = "test_mfb_chip"
    poverty_guideline_table = "48-state"
    pregnant_member_count_for_others = "1"
    chip_income_limit_fpl = 300
    medicaid_child_income_limit_under_1_fpl = 200
    medicaid_child_income_limit_1_to_5_fpl = 150
    medicaid_child_income_limit_6_to_18_fpl = 140
    pregnant_women_option = True
    medicaid_pregnancy_income_limit_fpl = 185
    # 12,000,000 / 10,000 / 12 = 100 a month.
    separate_chip_benefit_spending = 12_000_000
    separate_chip_average_monthly_enrollment = 10_000


class CountsTwoChip(StateChip):
    program_code = "test_mfb_chip_two"
    pregnant_member_count_for_others = "2"


class CountsExpectedChip(StateChip):
    program_code = "test_mfb_chip_expected"
    pregnant_member_count_for_others = "herself_plus_expected"


class NoPregnancyChip(StateChip):
    program_code = "test_mfb_chip_no_pregnancy"
    pregnant_women_option = False


class StateExcludesChip(StateChip):
    program_code = "test_mfb_chip_state_exclusion"
    state_magi_excluded_income_types = ("investment",)


class NoValueInputsChip(StateChip):
    program_code = "test_mfb_chip_no_value"
    separate_chip_benefit_spending = None


class HalfDollarChip(StateChip):
    program_code = "test_mfb_chip_half_dollar"
    # 1,260,000 / 1,000 / 12 = 105 a month; 1,266,000 / 1,000 / 12 = 105.50.
    separate_chip_benefit_spending = 1_266_000
    separate_chip_average_monthly_enrollment = 1_000


class StateFcep(MfbChipFcep):
    program_code = "test_mfb_chip_fcep"
    poverty_guideline_table = "48-state"
    pregnant_member_count_for_others = "1"
    fcep_income_limit_fpl = 200


_next_id = iter(range(1, 10_000))


def make_member(age: Optional[int] = 8, pregnant: Optional[bool] = False, insurance: tuple = ()) -> Mock:
    member = Mock()
    member.id = next(_next_id)
    member.calc_age.return_value = age
    member.pregnant = pregnant
    member.has_insurance_types.side_effect = lambda types: any(t in insurance for t in types)
    return member


def make_calculator(
    members: list,
    income: float = 0,
    household_size: Optional[int] = None,
    cls: type = StateChip,
    excluded_income: Optional[dict] = None,
    missing: tuple = (),
) -> MfbChipCommon:
    """`income` is countable; `excluded_income` maps income types to amounts the exclude list should drop."""
    excluded_income = excluded_income or {}

    def gross_income(frequency: str, types: list, exclude=()) -> float:
        dropped = sum(amount for kind, amount in excluded_income.items() if kind in exclude)
        return float(income + sum(excluded_income.values()) - dropped)

    screen = Mock()
    screen.household_size = len(members) if household_size is None else household_size
    screen.calc_gross_income.side_effect = gross_income
    screen.household_members.all.return_value = members

    program = Mock()
    program.year.get_limit.side_effect = lambda size: FPL_2026[size]

    return cls(screen, program, {}, Dependencies(missing))


def run(calculator: MfbChipCommon) -> Eligibility:
    return calculator.calc()


def income_at(percent: float, size: int = 3) -> float:
    """Yearly income at `percent`% of the poverty line for `size`, before the disregard."""
    return FPL_2026[size] * percent / 100


class TestClassContract(SimpleTestCase):
    def test_bases_are_abstract_and_states_are_not(self):
        for cls in (MfbChipCommon, MfbChip, MfbChipFcep):
            self.assertTrue(cls._abstract)
        self.assertFalse(StateChip._abstract)
        self.assertFalse(StateFcep._abstract)

    def test_unsupported_poverty_table_fails_at_class_creation(self):
        with self.assertRaises(TypeError):

            class AlaskaChip(StateChip):
                program_code = "test_alaska_chip"
                poverty_guideline_table = "Alaska"

    def test_missing_family_size_election_fails_at_class_creation(self):
        with self.assertRaises(TypeError):

            class NoElectionFcep(MfbChipFcep):
                program_code = "test_no_election"
                poverty_guideline_table = "48-state"

    def test_missing_dependency_drops_program(self):
        for field in ("age", "household_size", "income_amount", "insurance"):
            with self.subTest(field=field):
                with self.assertRaises(DependencyError):
                    run(make_calculator([make_member()], missing=(field,)))

    def test_pregnant_is_not_a_dependency(self):
        self.assertNotIn("pregnant", StateChip.dependencies)


class TestChildRoute(SimpleTestCase):
    """`age_under_19`, `child_income_band`, `not_enrolled_in_medicaid` and `no_other_coverage`."""

    def household(self, child: Mock, percent: float) -> list:
        return [make_member(age=35), make_member(age=33), child]

    def eligible(self, child: Mock, percent: float, cls: type = StateChip) -> bool:
        members = self.household(child, percent)
        calculator = make_calculator(members, income=income_at(percent), cls=cls)
        e = run(calculator)
        return next(m for m in e.eligible_members if m.member is child).eligible

    def test_in_the_band(self):
        self.assertTrue(self.eligible(make_member(age=8), 250))

    def test_disregard_applies_at_the_ceiling(self):
        # 305% less 5 is 300, at the limit; one dollar more is over.
        self.assertTrue(self.eligible(make_member(age=8), 305))
        child = make_member(age=8)
        members = self.household(child, 0)
        e = run(make_calculator(members, income=income_at(305) + 1))
        self.assertFalse(e.eligible_members[2].eligible)

    def test_disregard_applies_at_the_medicaid_floor(self):
        # 145% less 5 is 140, inside Medicaid for ages 6-18; one dollar more is CHIP.
        self.assertFalse(self.eligible(make_member(age=8), 145))
        child = make_member(age=8)
        e = run(make_calculator(self.household(child, 0), income=income_at(145) + 1))
        self.assertTrue(e.eligible_members[2].eligible)

    def test_medicaid_floor_follows_age_band(self):
        # 152% less 5 is 147: above 140 (6-18), inside 150 (1-5) and 200 (infant).
        self.assertTrue(self.eligible(make_member(age=6), 152))
        self.assertFalse(self.eligible(make_member(age=5), 152))
        self.assertFalse(self.eligible(make_member(age=1), 152))
        self.assertFalse(self.eligible(make_member(age=0), 152))
        # 210% less 5 is 205, above the infant limit.
        self.assertTrue(self.eligible(make_member(age=0), 210))

    def test_pregnant_child_uses_higher_of_age_and_pregnancy_limits(self):
        # Household of 2 plus her own expected child: a family of 3. At 180% less 5, 175 is
        # above 140 for her age but inside the 185 pregnancy limit; at 195% it is above both.
        child = make_member(age=16, pregnant=True)
        members = [make_member(age=35), child]
        e = run(make_calculator(members, income=income_at(180, 3)))
        self.assertFalse(e.eligible_members[1].eligible)
        e = run(make_calculator(members, income=income_at(195, 3)))
        self.assertTrue(e.eligible_members[1].eligible)

    def test_nineteen_is_too_old_and_eighteen_is_not(self):
        self.assertFalse(self.eligible(make_member(age=19), 250))
        self.assertTrue(self.eligible(make_member(age=18), 250))

    def test_unknown_age_is_not_a_child(self):
        self.assertFalse(self.eligible(make_member(age=None), 250))

    def test_medicaid_bars(self):
        self.assertFalse(self.eligible(make_member(age=8, insurance=("medicaid",)), 250))

    def test_employer_and_private_coverage_bar(self):
        self.assertFalse(self.eligible(make_member(age=8, insurance=("employer",)), 250))
        self.assertFalse(self.eligible(make_member(age=8, insurance=("private",)), 250))

    def test_base_does_not_bar_chip_medicare_or_va(self):
        for kind in ("chp", "medicare", "va"):
            with self.subTest(kind=kind):
                self.assertTrue(self.eligible(make_member(age=8, insurance=(kind,)), 250))


class TestIncome(SimpleTestCase):
    def test_magi_excluded_types_are_left_out(self):
        child = make_member(age=8)
        members = [make_member(age=35), child]
        excluded = {kind: 100_000 for kind in MAGI_EXCLUDED_INCOME_TYPES}
        e = run(make_calculator(members, income=income_at(250, 2), excluded_income=excluded))
        self.assertTrue(e.eligible_members[1].eligible)

    def test_state_excluded_types_are_left_out(self):
        child = make_member(age=8)
        members = [make_member(age=35), child]
        investment = {"investment": 100_000}
        base = run(make_calculator(members, income=income_at(250, 2), excluded_income=investment))
        self.assertFalse(base.eligible_members[1].eligible)
        state = run(
            make_calculator(members, income=income_at(250, 2), excluded_income=investment, cls=StateExcludesChip)
        )
        self.assertTrue(state.eligible_members[1].eligible)


class TestFamilySize(SimpleTestCase):
    """42 CFR 435.603(b): her own expected child always; others' count by election."""

    def test_own_expected_child_always_counts(self):
        mother = make_member(age=30, pregnant=True)
        for cls in (StateChip, CountsTwoChip, CountsExpectedChip):
            with self.subTest(cls=cls.__name__):
                calculator = make_calculator([mother, make_member(age=32)], cls=cls)
                self.assertEqual(calculator.family_size(mother), 3)

    def test_others_by_election(self):
        mother = make_member(age=30, pregnant=True)
        child = make_member(age=6)
        members = [mother, make_member(age=32), child]
        for cls, expected in ((StateChip, 3), (CountsTwoChip, 4), (CountsExpectedChip, 4)):
            with self.subTest(cls=cls.__name__):
                self.assertEqual(make_calculator(members, cls=cls).family_size(child), expected)

    def test_two_pregnant_members_count_once_each(self):
        mother = make_member(age=40, pregnant=True)
        daughter = make_member(age=20, pregnant=True)
        calculator = make_calculator([mother, daughter], cls=CountsExpectedChip)
        self.assertEqual(calculator.family_size(mother), 4)
        self.assertEqual(calculator.family_size(daughter), 4)
        self.assertEqual(make_calculator([mother, daughter]).family_size(mother), 3)

    def test_blank_pregnancy_counts_as_not_pregnant(self):
        member = make_member(age=30, pregnant=None)
        other = make_member(age=6)
        calculator = make_calculator([member, other], cls=CountsExpectedChip)
        self.assertEqual(calculator.family_size(member), 2)
        self.assertEqual(calculator.family_size(other), 2)

    def test_family_size_moves_the_child_test(self):
        # 43,000 for a family of 3 is 157% (CHIP); of 4, 130% (Medicaid).
        mother = make_member(age=30, pregnant=True)
        child = make_member(age=6)
        members = [mother, make_member(age=32), child]
        self.assertTrue(run(make_calculator(members, income=43_000)).eligible_members[2].eligible)
        counted = run(make_calculator(members, income=43_000, cls=CountsExpectedChip))
        self.assertFalse(counted.eligible_members[2].eligible)


class TestPregnantRoute(SimpleTestCase):
    def mother_eligible(self, percent: float, cls: type = StateChip, **member) -> bool:
        member.setdefault("age", 27)
        member.setdefault("pregnant", True)
        mother = make_member(**member)
        # Household of 2 plus her expected child: family of 3.
        e = run(make_calculator([mother, make_member(age=29)], income=income_at(percent, 3), cls=cls))
        return e.eligible_members[0].eligible

    def test_in_the_band(self):
        self.assertTrue(self.mother_eligible(250))

    def test_disregard_at_the_pregnancy_medicaid_limit(self):
        self.assertFalse(self.mother_eligible(190))
        self.assertTrue(self.mother_eligible(190.01))

    def test_ceiling_is_the_chip_limit(self):
        self.assertTrue(self.mother_eligible(305))
        self.assertFalse(self.mother_eligible(305.01))

    def test_not_pregnant_or_blank_does_not_qualify(self):
        self.assertFalse(self.mother_eligible(250, pregnant=False))
        self.assertFalse(self.mother_eligible(250, pregnant=None))

    def test_state_without_the_option(self):
        self.assertFalse(self.mother_eligible(250, cls=NoPregnancyChip))

    def test_coverage_bars(self):
        for kind in ("medicaid", "employer", "private"):
            with self.subTest(kind=kind):
                self.assertFalse(self.mother_eligible(250, insurance=(kind,)))

    def test_minor_uses_higher_of_pregnancy_and_age_limits(self):
        class HighTeenLimitChip(StateChip):
            program_code = "test_mfb_chip_high_teen"
            medicaid_child_income_limit_6_to_18_fpl = 200

        # 200% less 5 is 195: above 185 for an adult, inside 200 for a 16-year-old.
        self.assertTrue(self.mother_eligible(200, cls=HighTeenLimitChip))
        self.assertFalse(self.mother_eligible(200, cls=HighTeenLimitChip, age=16))

    def test_unknown_age_uses_pregnancy_limit(self):
        self.assertTrue(self.mother_eligible(250, age=None))


class TestValue(SimpleTestCase):
    def test_child_value_is_section_7_monthly_times_12(self):
        child = make_member(age=8)
        e = run(make_calculator([make_member(age=35), child], income=income_at(250, 2)))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 100 * 12)

    def test_section_7_rounds_half_up(self):
        child = make_member(age=8)
        e = run(make_calculator([make_member(age=35), child], income=income_at(250, 2), cls=HalfDollarChip))
        self.assertEqual(e.value, 106 * 12)

    def test_pregnancy_route_only_is_eligible_with_no_value(self):
        mother = make_member(age=27, pregnant=True)
        e = run(make_calculator([mother, make_member(age=29)], income=income_at(250, 3)))
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 0)

    def test_values_each_eligible_child(self):
        members = [make_member(age=40), make_member(age=4), make_member(age=10)]
        e = run(make_calculator(members, income=income_at(250)))
        self.assertEqual(e.value, 2 * 100 * 12)

    def test_state_with_no_value_inputs_raises(self):
        child = make_member(age=8)
        calculator = make_calculator([make_member(age=35), child], income=income_at(250, 2), cls=NoValueInputsChip)
        with self.assertRaises(NotImplementedError):
            run(calculator)

    def test_ineligible_household(self):
        e = run(make_calculator([make_member(age=35), make_member(age=8)], income=income_at(400, 2)))
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestFcep(SimpleTestCase):
    """`fcep_pregnancy` and `fcep_income_limit`, on its own program."""

    def eligible(self, percent: float, **member) -> bool:
        member.setdefault("age", 27)
        member.setdefault("pregnant", True)
        mother = make_member(**member)
        e = run(make_calculator([mother, make_member(age=29)], income=income_at(percent, 3), cls=StateFcep))
        return e.eligible

    def test_at_and_over_the_limit(self):
        self.assertTrue(self.eligible(205))
        self.assertFalse(self.eligible(205.01))

    def test_no_lower_bound(self):
        self.assertTrue(self.eligible(0))

    def test_must_be_pregnant(self):
        self.assertFalse(self.eligible(150, pregnant=False))
        self.assertFalse(self.eligible(150, pregnant=None))

    def test_coverage_bars(self):
        for kind in ("medicaid", "employer", "private"):
            with self.subTest(kind=kind):
                self.assertFalse(self.eligible(150, insurance=(kind,)))

    def test_no_value(self):
        mother = make_member(age=27, pregnant=True)
        e = run(make_calculator([mother, make_member(age=29)], income=income_at(150, 3), cls=StateFcep))
        self.assertEqual(e.value, 0)
