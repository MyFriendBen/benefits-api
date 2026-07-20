"""
Unit tests for the KsLieap calculator.

Coverage maps to spec.md's Eligibility Criteria and the 12 Test Scenarios.

Screenable criteria exercised here:
- Criterion 1: household gross income at or below 150% FPL.
- Criterion 2: categorical eligibility (SNAP / TANF / SSI) bypasses the income
  test.
- Criterion 4: responsibility for home energy costs, inferred from a
  rent / mortgage / heating expense (nc_lieap precedent).

Not tested here (handled outside the calculator):
- Criterion 3 (KS residency) — white-label routing / location picker.
- Criterion 5 (citizenship) — config `legal_status_required`.
- "Already receiving LIEAP" (Scenario 7) — the framework's `already_has` flag
  driven by the `has_ks_lieap` current-benefit field, not calculator logic. The
  calculator itself still finds such a household eligible; see
  TestKsLieapScenario7.

Benefit value is a flat $680/year for every eligible household.

The 100% FPL limits used below are chosen so that 1.5x equals the exact
per-household-size 150% FPL dollar thresholds Kansas DCF publishes, so the
"barely eligible" / "just above" boundary scenarios test the real cutoffs.
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.ks import ks_calculators
from programs.programs.ks.lieap.calculator import KsLieap
from programs.programs.calc import ProgramCalculator, Eligibility


# 100% FPL by household size such that 1.5x matches DCF's published 150% caps.
FPL_100 = {
    1: 15_648,  # 1.5x = 23,472
    2: 21_152,  # 1.5x = 31,728
    3: 26_648,  # 1.5x = 39,972
    4: 32_152,  # 1.5x = 48,228
    5: 37_648,  # 1.5x = 56,472
}


def make_calculator(
    income=0,
    ssi_income=0,
    household_size=1,
    has_energy_expense=True,
    has_snap=False,
    has_tanf=False,
    has_ssi_benefit=False,
    members=None,
):
    if members is None:
        members = [Mock() for _ in range(household_size)]

    def gross_income(_freq, types, exclude=None):
        return ssi_income if "sSI" in types else income

    def has_base_benefit(base_program):
        return {"snap": has_snap, "tanf": has_tanf, "ssi": has_ssi_benefit}.get(base_program, False)

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(side_effect=gross_income)
    mock_screen.has_expense = Mock(return_value=has_energy_expense)
    mock_screen.has_base_benefit = Mock(side_effect=has_base_benefit)
    mock_screen.household_members.all = Mock(return_value=members)

    mock_program = Mock()
    mock_program.year.get_limit.return_value = FPL_100.get(household_size, FPL_100[1])

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return KsLieap(mock_screen, mock_program, {}, mock_missing_deps)


def run_household_eligible(calc):
    e = Eligibility()
    calc.household_eligible(e)
    return e


class TestKsLieapClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(KsLieap, ProgramCalculator))

    def test_is_registered_in_ks_calculators(self):
        self.assertIn("ks_lieap", ks_calculators)
        self.assertEqual(ks_calculators["ks_lieap"], KsLieap)

    def test_fpl_percent_is_150(self):
        self.assertEqual(KsLieap.fpl_percent, 1.5)

    def test_amount_is_680(self):
        self.assertEqual(KsLieap.amount, 680)

    def test_energy_expense_types(self):
        self.assertEqual(set(KsLieap.expenses), {"rent", "mortgage", "heating"})

    def test_income_fields_in_dependencies(self):
        self.assertIn("income_amount", KsLieap.dependencies)
        self.assertIn("income_frequency", KsLieap.dependencies)
        self.assertIn("household_size", KsLieap.dependencies)


class TestKsLieapIncomeEligibility(TestCase):
    """Criterion 1 — gross income at or below 150% FPL."""

    def test_income_below_cap_is_eligible(self):
        self.assertTrue(run_household_eligible(make_calculator(income=10_000, household_size=1)).eligible)

    def test_income_exactly_at_cap_is_eligible(self):
        # inclusive comparison (<=): 1-person cap is 23,472
        self.assertTrue(run_household_eligible(make_calculator(income=23_472, household_size=1)).eligible)

    def test_income_just_above_cap_is_ineligible(self):
        self.assertFalse(run_household_eligible(make_calculator(income=23_473, household_size=1)).eligible)

    def test_income_pass_message_included(self):
        e = run_household_eligible(make_calculator(income=10_000, household_size=1))
        self.assertTrue(len(e.pass_messages) > 0)

    def test_income_fail_message_included(self):
        e = run_household_eligible(make_calculator(income=30_000, household_size=1))
        self.assertTrue(len(e.fail_messages) > 0)


class TestKsLieapEnergyCostResponsibility(TestCase):
    """Criterion 4 — must be responsible for home energy costs."""

    def test_with_energy_expense_is_eligible(self):
        self.assertTrue(run_household_eligible(make_calculator(income=10_000, has_energy_expense=True)).eligible)

    def test_without_energy_expense_is_ineligible(self):
        self.assertFalse(run_household_eligible(make_calculator(income=10_000, has_energy_expense=False)).eligible)


class TestKsLieapCategoricalEligibility(TestCase):
    """Criterion 2 — SNAP / TANF / SSI receipt bypasses the income test."""

    def test_snap_bypasses_income(self):
        e = run_household_eligible(make_calculator(income=999_999, household_size=2, has_snap=True))
        self.assertTrue(e.eligible)

    def test_tanf_bypasses_income(self):
        e = run_household_eligible(make_calculator(income=999_999, household_size=2, has_tanf=True))
        self.assertTrue(e.eligible)

    def test_ssi_benefit_bypasses_income(self):
        e = run_household_eligible(make_calculator(income=999_999, household_size=2, has_ssi_benefit=True))
        self.assertTrue(e.eligible)

    def test_ssi_income_stream_bypasses_income(self):
        # has_ssi_or_ssi_income: an sSI income stream counts even if the tile is untouched
        e = run_household_eligible(make_calculator(income=999_999, household_size=2, ssi_income=6_000))
        self.assertTrue(e.eligible)

    def test_categorical_still_requires_energy_expense(self):
        # Criterion 2 bypasses income only, not Criterion 4
        e = run_household_eligible(
            make_calculator(income=999_999, household_size=2, has_snap=True, has_energy_expense=False)
        )
        self.assertFalse(e.eligible)

    def test_no_categorical_and_over_income_is_ineligible(self):
        e = run_household_eligible(make_calculator(income=999_999, household_size=2))
        self.assertFalse(e.eligible)

    def test_categorically_eligible_helper(self):
        self.assertTrue(make_calculator(has_snap=True)._categorically_eligible())
        self.assertTrue(make_calculator(has_tanf=True)._categorically_eligible())
        self.assertTrue(make_calculator(has_ssi_benefit=True)._categorically_eligible())
        self.assertTrue(make_calculator(ssi_income=1)._categorically_eligible())
        self.assertFalse(make_calculator()._categorically_eligible())


class TestKsLieapValue(TestCase):
    def test_household_value_is_680(self):
        self.assertEqual(make_calculator().household_value(), 680)

    def test_eligible_household_value_is_680(self):
        e = make_calculator(income=10_000, household_size=1).calc()
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 680)

    def test_ineligible_household_value_is_zero(self):
        e = make_calculator(income=999_999, household_size=1).calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)


class TestKsLieapScenarios(TestCase):
    """End-to-end calc() coverage for each spec Test Scenario."""

    def _calc(self, **kwargs):
        return make_calculator(**kwargs).calc()

    def test_scenario_1_single_adult_well_below_cap(self):
        e = self._calc(income=14_400, household_size=1)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 680)

    def test_scenario_2_two_person_near_ceiling(self):
        e = self._calc(income=31_680, household_size=2)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 680)

    def test_scenario_3_three_person_just_below_cap(self):
        e = self._calc(income=39_840, household_size=3)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 680)

    def test_scenario_4_four_person_exactly_at_cap(self):
        e = self._calc(income=48_228, household_size=4)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 680)

    def test_scenario_5_single_adult_just_above_cap(self):
        e = self._calc(income=23_640, household_size=1)
        self.assertFalse(e.eligible)

    def test_scenario_6_senior_social_security(self):
        # $900/mo SS retirement = $10,800/yr, aggregated via "all"
        e = self._calc(income=10_800, household_size=1)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 680)

    def test_scenario_7_already_receiving_lieap_is_eligible_at_calculator_level(self):
        # Income-eligible with an energy expense -> the calculator finds them
        # eligible. The "already receiving" exclusion is applied by the framework
        # via the has_ks_lieap current-benefit field / already_has flag, not here.
        e = self._calc(income=10_800, household_size=2)
        self.assertTrue(e.eligible)

    def test_scenario_8_not_responsible_for_energy_costs(self):
        e = self._calc(income=24_000, household_size=2, has_energy_expense=False)
        self.assertFalse(e.eligible)

    def test_scenario_9_mixed_citizenship_income_eligible(self):
        # $1,800 + $1,200 = $3,000/mo = $36,000/yr; citizenship handled by config
        members = [Mock(), Mock(), Mock(), Mock()]
        e = self._calc(income=36_000, household_size=4, members=members)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 680)

    def test_scenario_10_five_person_household(self):
        e = self._calc(income=43_200, household_size=5)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 680)

    def test_scenario_11_zero_income(self):
        e = self._calc(income=0, household_size=1)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 680)

    def test_scenario_12_over_income_but_snap_categorical(self):
        # $38,400/yr is above the 2-person cap ($31,728) but SNAP receipt qualifies
        e = self._calc(income=38_400, household_size=2, has_snap=True)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 680)

    def test_scenario_12_counterpart_over_income_without_snap_is_ineligible(self):
        e = self._calc(income=38_400, household_size=2, has_snap=False)
        self.assertFalse(e.eligible)
