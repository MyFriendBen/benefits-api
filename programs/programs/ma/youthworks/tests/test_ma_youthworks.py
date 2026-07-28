"""
Unit tests for MaYouthworks calculator class.

Eligibility requirements (see spec.md):
- Age 14–25 (per member)
- Family gross income <= 200% of the 2025 Federal Poverty Guidelines (household)
- Massachusetts residency — enforced upstream by white-label routing, NOT in the
  calculator (the program operates statewide across all 16 MassHire regions, so
  there is no sub-state/geographic check). Scenarios 9 and 15 exercise that routing
  layer, not calculator logic; they are documented here but cannot be expressed as
  calculator unit tests (see TestMaYouthworksResidencyRouting).
- Risk/demographic factor (criterion 4) is a data gap; an inclusivity assumption is
  applied (no check), so there is no calculator branch to test.

Benefit value: $2,400/yr per eligible youth, summed across eligible members.

Real 2025 FPL base (100%) values used in fixtures, by household size:
    {1: 15650, 2: 21150, 3: 26650, 4: 32150}
200% thresholds: {1: 31300, 2: 42300, 3: 53300, 4: 64300}
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.ma import ma_calculators
from programs.programs.ma.youthworks.calculator import MaYouthworks
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility

# Real 2025 Federal Poverty Guideline base (100%) amounts by household size.
FPL_2025_BASE = {1: 15650, 2: 21150, 3: 26650, 4: 32150}


def make_member(age):
    """Create a mock household member with an age."""
    member = Mock()
    member.age = age
    return member


def make_calculator(members, household_yearly_income, household_size=None):
    """Build a MaYouthworks calculator with a mocked screen/program.

    - members: list of mock members returned by household_members.all()
    - household_yearly_income: value returned by screen.calc_gross_income("yearly", ["all"])
    - household_size: defaults to len(members); drives which FPL base limit is used
    """
    if household_size is None:
        household_size = len(members)

    mock_program = Mock()
    mock_program.year.get_limit = Mock(side_effect=lambda size: FPL_2025_BASE[size])

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.household_members.all = Mock(return_value=members)
    mock_screen.calc_gross_income = Mock(return_value=household_yearly_income)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return MaYouthworks(mock_screen, mock_program, {}, mock_missing_deps)


# ---------------------------------------------------------------------------
# Class attributes / registration
# ---------------------------------------------------------------------------


class TestMaYouthworksClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(MaYouthworks, ProgramCalculator))

    def test_is_registered_in_ma_calculators(self):
        self.assertIn("ma_youthworks", ma_calculators)
        self.assertEqual(ma_calculators["ma_youthworks"], MaYouthworks)

    def test_min_age_is_14(self):
        self.assertEqual(MaYouthworks.min_age, 14)

    def test_max_age_is_25(self):
        self.assertEqual(MaYouthworks.max_age, 25)

    def test_fpl_percent_is_2(self):
        self.assertEqual(MaYouthworks.fpl_percent, 2)

    def test_member_amount_is_annual_2400(self):
        self.assertEqual(MaYouthworks.member_amount, 2_400)


# ---------------------------------------------------------------------------
# Member eligibility — age gate (14–25)
# ---------------------------------------------------------------------------


class TestMaYouthworksMemberEligibility(TestCase):
    def _run(self, age):
        calc = make_calculator([make_member(age)], household_yearly_income=0)
        e = MemberEligibility(make_member(age))
        calc.member_eligible(e)
        return e.eligible

    def test_age_14_minimum_is_eligible(self):  # Scenario 6
        self.assertTrue(self._run(14))

    def test_age_13_below_minimum_is_ineligible(self):  # Scenario 7
        self.assertFalse(self._run(13))

    def test_age_25_maximum_is_eligible(self):  # Scenario 8
        self.assertTrue(self._run(25))

    def test_age_24_within_range_is_eligible(self):  # Scenario 10
        self.assertTrue(self._run(24))

    def test_age_26_above_maximum_is_ineligible(self):  # Scenario 11
        self.assertFalse(self._run(26))

    def test_age_16_typical_is_eligible(self):  # Scenario 1
        self.assertTrue(self._run(16))

    def test_age_none_is_ineligible(self):
        self.assertFalse(self._run(None))


# ---------------------------------------------------------------------------
# Household eligibility — income gate (<= 200% FPL)
# ---------------------------------------------------------------------------


class TestMaYouthworksIncomeEligibility(TestCase):
    """Income gate uses the real 2025 FPL tables at 200%."""

    def _run(self, household_yearly_income, household_size):
        calc = make_calculator(
            [make_member(16)], household_yearly_income=household_yearly_income, household_size=household_size
        )
        e = Eligibility()
        e.add_member_eligibility(MemberEligibility(make_member(16)))
        calc.household_eligible(e)
        return e.eligible

    def test_income_just_below_200_fpl_hh3_is_eligible(self):  # Scenario 3
        # $4,400/mo = $52,800/yr, below $53,300 (200% FPL for HH3)
        self.assertTrue(self._run(52_800, 3))

    def test_income_at_100_fpl_hh3_is_eligible(self):  # Scenario 4
        # ~$26,650/yr, ~100% FPL, well below the 200% ceiling
        self.assertTrue(self._run(26_652, 3))

    def test_income_exactly_at_200_fpl_hh3_is_eligible(self):
        # Boundary: income == limit ($53,300) should pass (<=).
        self.assertTrue(self._run(53_300, 3))

    def test_income_just_above_200_fpl_hh3_is_ineligible(self):  # Scenario 5
        # $4,500/mo = $54,000/yr, above $53,300
        self.assertFalse(self._run(54_000, 3))

    def test_income_above_200_fpl_hh1_is_ineligible(self):  # Scenario 16
        # $2,800/mo = $33,600/yr, above $31,300 (200% FPL for HH1)
        self.assertFalse(self._run(33_600, 1))

    def test_zero_income_hh1_is_eligible(self):  # Scenario 2
        self.assertTrue(self._run(0, 1))


# ---------------------------------------------------------------------------
# End-to-end calc() — full acceptance scenarios
# ---------------------------------------------------------------------------


class TestMaYouthworksScenarios(TestCase):
    """Each acceptance-criteria scenario run end-to-end through calc().

    Location is mocked out (residency is a routing concern), so these focus on the
    calculator's age + income + per-member value logic.
    """

    def _calc(self, members, household_yearly_income, household_size=None):
        calc = make_calculator(members, household_yearly_income, household_size)
        return calc.calc()

    def test_scenario_1_eligible_16yo_boston(self):
        e = self._calc([make_member(40), make_member(16), make_member(12)], 30_000)  # $2,500/mo
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_400)

    def test_scenario_2_eligible_17yo_springfield_hh1(self):
        e = self._calc([make_member(17)], 0)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_400)

    def test_scenario_3_income_just_below_200fpl_eligible(self):
        e = self._calc([make_member(46), make_member(16), make_member(11)], 52_800)  # $4,400/mo
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_400)

    def test_scenario_4_income_at_100fpl_eligible(self):
        e = self._calc([make_member(46), make_member(16), make_member(11)], 26_652)  # $2,221/mo
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_400)

    def test_scenario_5_income_just_above_200fpl_ineligible(self):
        e = self._calc([make_member(40), make_member(16), make_member(11)], 54_000)  # $4,500/mo
        self.assertFalse(e.eligible)

    def test_scenario_6_age_exactly_minimum_14_eligible(self):
        e = self._calc([make_member(46), make_member(14), make_member(9)], 24_000)  # $2,000/mo
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_400)

    def test_scenario_7_age_just_below_minimum_13_ineligible(self):
        # No household member is 14–25 → not one member eligible → household ineligible.
        e = self._calc([make_member(40), make_member(13), make_member(6)], 24_000)
        self.assertFalse(e.eligible)

    def test_scenario_8_age_exactly_maximum_25_eligible(self):
        e = self._calc([make_member(25)], 14_400)  # $1,200/mo, HH1
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_400)

    def test_scenario_9_eligible_location_lawrence(self):
        # Location is not a calculator check; verifies the youth is otherwise eligible.
        e = self._calc([make_member(46), make_member(16), make_member(11)], 21_600)  # $1,800/mo
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_400)

    def test_scenario_10_upper_age_boundary_24_eligible(self):
        e = self._calc([make_member(24)], 14_400)  # $1,200/mo, HH1
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_400)

    def test_scenario_11_age_just_above_maximum_26_ineligible(self):
        e = self._calc([make_member(26)], 14_400)
        self.assertFalse(e.eligible)

    def test_scenario_12_mixed_household_one_eligible_youth(self):
        # 16yo eligible, 12yo below minimum → value counts only the 16yo.
        members = [make_member(46), make_member(44), make_member(16), make_member(12)]
        e = self._calc(members, 30_000, household_size=4)  # ($2,000+$500)/mo
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_400)

    def test_scenario_13_multiple_eligible_youth_values_sum(self):
        # Two eligible youth (17 and 15) → $2,400 × 2 = $4,800.
        members = [make_member(46), make_member(44), make_member(17), make_member(15)]
        e = self._calc(members, 31_200, household_size=4)  # ($1,800+$800)/mo
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 4_800)

    def test_scenario_14_youth_turning_14_this_month_eligible(self):
        e = self._calc([make_member(46), make_member(14)], 14_400, household_size=2)  # $1,200/mo
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 2_400)

    def test_scenario_16_over_income_hh1_ineligible(self):
        e = self._calc([make_member(22)], 33_600)  # $2,800/mo, HH1, above $31,300
        self.assertFalse(e.eligible)


class TestMaYouthworksResidencyRouting(TestCase):
    """Scenarios 9 (Lawrence, eligible) and 15 (Providence RI, ineligible) test
    Massachusetts residency, which is enforced by white-label routing upstream of
    the calculator — the MA calculators only run for MA screens. There is no
    location/ZIP branch inside MaYouthworks to unit-test, so the out-of-state
    exclusion (Scenario 15) cannot be expressed as a calculator unit test; it is
    covered by the routing layer. The in-state eligible case (Scenario 9) is
    exercised in TestMaYouthworksScenarios.test_scenario_9_eligible_location_lawrence.
    """

    def test_calculator_has_no_location_check(self):
        # Documents the design decision: statewide program, no sub-state gate.
        import inspect

        source = inspect.getsource(MaYouthworks)
        self.assertNotIn("county", source)
        self.assertNotIn("zipcode", source.replace('"income_frequency"', ""))
