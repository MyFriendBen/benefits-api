"""
Unit tests for TxFpp (Texas Family Planning Program) — hybrid PolicyEngine calculator.

PolicyEngine owns the income determination (countable-income formula + 250% FPG limit,
read back as ``tx_fpp_income_eligible``) and age (``tx_fpp_age_eligible``). MFB layers on:
  - §4140 adjunctive bypass — SNAP/WIC (CurrentBenefit join table) or CHIP (per-member
    insurance) makes the household income-eligible regardless of the FPG test.
  - §4100 insurance rule — only full Medicaid disqualifies; Emergency Medicaid and other
    coverage remain eligible.

Because these run without the live PolicyEngine API, PE's determination is mocked exactly
as PE would return it for the scenario (get_member_dependency_value = tx_fpp_age_eligible;
get_dependency_value = tx_fpp_income_eligible). Assertions are on the MFB-side output:
the per-member $266.84 value and the overlay routing.
"""

from unittest.mock import Mock, MagicMock

from django.test import TestCase

from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from programs.programs.policyengine.calculators.dependencies import member as member_deps
from programs.programs.policyengine.calculators.dependencies import spm as spm_deps
from programs.programs.policyengine.calculators.dependencies.household import TxStateCodeDependency
from programs.programs.tx.pe import tx_pe_calculators, tx_member_calculators
from programs.programs.tx.pe.member import TxFpp

ANNUAL_BENEFIT = 266.84


def make_member(medicaid=False, emergency_medicaid=False, employer=False, none=True, member_id=1):
    """Mock a household member with an insurance object. Age is decided by PolicyEngine
    (mocked via get_member_dependency_value), so member.age is not read here."""
    member = Mock()
    member.id = member_id
    flags = {
        "medicaid": medicaid,
        "emergency_medicaid": emergency_medicaid,
        "employer": employer,
        "none": none,
    }
    insurance = Mock()
    insurance.has_insurance_types = Mock(side_effect=lambda types: any(flags.get(t, False) for t in types))
    member.insurance = insurance
    return member


def make_calculator(
    age_eligible=1,
    income_eligible=1,
    current_benefits=None,
    has_chp=False,
    members=None,
):
    """Create a TxFpp calculator with PolicyEngine's determination mocked.

    Args:
        age_eligible: PE's tx_fpp_age_eligible (1/0) — returned for every member.
        income_eligible: PE's spm-unit tx_fpp_income_eligible (1/0).
        current_benefits: name_abbreviated strings in the CurrentBenefit join table
            (e.g. ["tx_snap", "tx_wic"]) — drives has_benefit(). tx_chip is never a
            current benefit, so use has_chp for CHIP.
        has_chp: whether a member has CHIP coverage (per-member insurance flag).
    """
    benefits = set(current_benefits or [])

    screen = Mock()
    screen.has_benefit = Mock(side_effect=lambda name_abbreviated: name_abbreviated in benefits)
    screen.has_insurance_types = Mock(side_effect=lambda types, strict=True: has_chp and "chp" in types)
    screen.household_members.all = Mock(return_value=members if members is not None else [])

    missing_deps = Mock()
    missing_deps.has = Mock(return_value=False)

    calc = TxFpp(screen, Mock(), missing_deps)
    calc._sim = MagicMock()
    # PolicyEngine's determination (would otherwise hit the live sim):
    calc.get_member_dependency_value = Mock(return_value=age_eligible)
    calc.get_dependency_value = Mock(return_value=income_eligible)
    return calc


class TestTxFppWiring(TestCase):
    def test_is_policyengine_members_calculator(self):
        self.assertTrue(issubclass(TxFpp, PolicyEngineMembersCalculator))

    def test_is_registered_in_tx_pe_calculators(self):
        self.assertIs(tx_pe_calculators.get("tx_fpp"), TxFpp)
        self.assertIs(tx_member_calculators.get("tx_fpp"), TxFpp)

    def test_member_amount_is_annual_benefit(self):
        self.assertAlmostEqual(TxFpp.member_amount, ANNUAL_BENEFIT)

    def test_reads_pe_eligibility_sub_variables(self):
        self.assertIn(member_deps.TxFppAgeEligible, TxFpp.pe_outputs)
        self.assertIn(spm_deps.TxFppIncomeEligible, TxFpp.pe_outputs)

    def test_feeds_income_and_state_to_pe(self):
        self.assertIn(TxStateCodeDependency, TxFpp.pe_inputs)
        self.assertIn(member_deps.AgeDependency, TxFpp.pe_inputs)
        self.assertIn(member_deps.EmploymentIncomeDependency, TxFpp.pe_inputs)


class TestTxFppMemberValue(TestCase):
    """member_value: age + insurance overlays against PE's eligibility flags."""

    def test_age_and_income_eligible_uninsured_gets_benefit(self):
        calc = make_calculator(age_eligible=1, income_eligible=1)
        self.assertAlmostEqual(calc.member_value(make_member()), ANNUAL_BENEFIT)

    def test_age_ineligible_is_zero(self):
        """PE's tx_fpp_age_eligible = 0 (over 64, or no recorded age)."""
        calc = make_calculator(age_eligible=0, income_eligible=1)
        self.assertEqual(calc.member_value(make_member()), 0)

    def test_no_minimum_age(self):
        """Criterion 1: no minimum age. MFB imposes no lower-age gate — age is delegated
        entirely to PE, so a member PE deems age-eligible (e.g. a young child) is not
        blocked by the calculator."""
        calc = make_calculator(age_eligible=1, income_eligible=1)
        self.assertAlmostEqual(calc.member_value(make_member()), ANNUAL_BENEFIT)

    def test_full_medicaid_is_zero(self):
        calc = make_calculator(age_eligible=1, income_eligible=1)
        self.assertEqual(calc.member_value(make_member(none=False, medicaid=True)), 0)

    def test_emergency_medicaid_remains_eligible(self):
        calc = make_calculator(age_eligible=1, income_eligible=1)
        self.assertAlmostEqual(calc.member_value(make_member(none=False, emergency_medicaid=True)), ANNUAL_BENEFIT)

    def test_employer_insurance_does_not_disqualify(self):
        calc = make_calculator(age_eligible=1, income_eligible=1)
        self.assertAlmostEqual(calc.member_value(make_member(none=False, employer=True)), ANNUAL_BENEFIT)

    def test_income_ineligible_no_bypass_is_zero(self):
        calc = make_calculator(age_eligible=1, income_eligible=0)
        self.assertEqual(calc.member_value(make_member()), 0)


class TestTxFppAdjunctiveBypass(TestCase):
    """§4140 — SNAP / WIC / CHIP enrollment bypasses PE's income test (income_eligible=0)."""

    def test_snap_bypasses_income_test(self):
        calc = make_calculator(income_eligible=0, current_benefits=["tx_snap"])
        self.assertAlmostEqual(calc.member_value(make_member()), ANNUAL_BENEFIT)

    def test_wic_bypasses_income_test(self):
        calc = make_calculator(income_eligible=0, current_benefits=["tx_wic"])
        self.assertAlmostEqual(calc.member_value(make_member()), ANNUAL_BENEFIT)

    def test_chip_bypasses_income_test(self):
        calc = make_calculator(income_eligible=0, has_chp=True)
        self.assertAlmostEqual(calc.member_value(make_member()), ANNUAL_BENEFIT)

    def test_bypass_does_not_override_age_or_medicaid(self):
        """The §4140 bypass only waives the income test — age and the Medicaid exclusion
        still apply."""
        over_age = make_calculator(age_eligible=0, income_eligible=0, current_benefits=["tx_snap"])
        self.assertEqual(over_age.member_value(make_member()), 0)
        on_medicaid = make_calculator(income_eligible=0, current_benefits=["tx_snap"])
        self.assertEqual(on_medicaid.member_value(make_member(none=False, medicaid=True)), 0)


class TestTxFppSpecScenarios(TestCase):
    """End-to-end calc(), one test per scenario in spec.md / the validation set
    (validations/.../import_validations/data/tx_fpp.json). Age and the 250% FPG income
    test are PolicyEngine's; each scenario sets age_eligible / income_eligible to PE's
    determination for that household. Household values are the pre-truncation floats
    (266.84 / 533.68); the validation layer truncates to 266 / 533.
    """

    def test_s0_eligible_low_income_no_insurance(self):
        """Eligible 25-year-old, low income, no insurance -> 266."""
        calc = make_calculator(age_eligible=1, income_eligible=1, members=[make_member()])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, ANNUAL_BENEFIT)

    def test_s1_age_64_upper_boundary_eligible(self):
        """Eligible 64-year-old at the maximum-age boundary (PE age_eligible=1) -> 266."""
        calc = make_calculator(age_eligible=1, income_eligible=1, members=[make_member()])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, ANNUAL_BENEFIT)

    def test_s2_medicaid_only_rule_employer_and_uninsured_both_eligible(self):
        """Employer-insured adult AND uninsured 18-year-old both eligible -> 533."""
        members = [
            make_member(member_id=1, none=False, employer=True),
            make_member(member_id=2, none=True),
        ]
        calc = make_calculator(age_eligible=1, income_eligible=1, members=members)
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, ANNUAL_BENEFIT * 2)

    def test_s3_age_65_above_maximum_ineligible(self):
        """Ineligible 65-year-old (PE age_eligible=0) despite low income and no insurance."""
        calc = make_calculator(age_eligible=0, income_eligible=1, members=[make_member()])
        e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_s4_emergency_medicaid_remains_eligible(self):
        """Emergency Medicaid recipient is underinsured (§4100) -> eligible, 266."""
        member = make_member(none=False, emergency_medicaid=True)
        calc = make_calculator(age_eligible=1, income_eligible=1, members=[member])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, ANNUAL_BENEFIT)

    def test_s5_employer_insurance_eligible(self):
        """Employer insurance does not disqualify under the Medicaid-only rule -> 266."""
        member = make_member(none=False, employer=True)
        calc = make_calculator(age_eligible=1, income_eligible=1, members=[member])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, ANNUAL_BENEFIT)

    def test_s6_sole_reproductive_member_full_medicaid_household_ineligible(self):
        """Household ineligible when its only member has full Medicaid."""
        member = make_member(none=False, medicaid=True)
        calc = make_calculator(age_eligible=1, income_eligible=1, members=[member])
        e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_s7_above_250_fpl_no_bypass_ineligible(self):
        """Ineligible 35-year-old above 250% FPL (PE income_eligible=0), no adjunctive benefit."""
        calc = make_calculator(age_eligible=1, income_eligible=0, members=[make_member()])
        e = calc.calc()
        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_s8_snap_adjunctive_bypass_above_income_eligible(self):
        """§4140: income above 250% FPL (income_eligible=0) but enrolled in SNAP -> 266."""
        calc = make_calculator(age_eligible=1, income_eligible=0, current_benefits=["tx_snap"], members=[make_member()])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, ANNUAL_BENEFIT)

    def test_s9_eligible_couple_two_members(self):
        """Couple (ages 55 and 30), no insurance, both qualify -> 533."""
        members = [make_member(member_id=1), make_member(member_id=2)]
        calc = make_calculator(age_eligible=1, income_eligible=1, members=members)
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, ANNUAL_BENEFIT * 2)

    def test_s10_parent_counts_medicaid_children_excluded(self):
        """Self-employed parent under threshold; Medicaid children excluded -> only parent, 266."""
        members = [
            make_member(member_id=1, none=True),
            make_member(member_id=2, none=False, medicaid=True),
            make_member(member_id=3, none=False, medicaid=True),
        ]
        calc = make_calculator(age_eligible=1, income_eligible=1, members=members)
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, ANNUAL_BENEFIT)
