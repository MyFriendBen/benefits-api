"""
Unit tests for KsKancareHcbs calculator class.

Eligibility (per spec):
- Hard gate: countable assets <= $2,000 (inclusive) for single applicants. Married
  applicants are NOT asset-gated (spousal-split data gap, handled inclusively).
- SSI auto-eligibility bypasses the asset test (has_ssi checkbox OR any SSI income stream).
- Income does NOT disqualify (cost-share threshold is informational only).
- Age does NOT filter (BI 0-64 + FE 65+ cover all ages).
- Disability flags do NOT gate (informational data gaps).
- Flat benefit value: $35,000/year.
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.ks import ks_calculators
from programs.programs.ks.kancare_hcbs.calculator import KsKancareHcbs
from programs.programs.calc import ProgramCalculator, Eligibility


def make_member(age=70, disabled=False, long_term_disability=False, ssi_income=0):
    """Create a mock household member.

    calc_gross_income is argument-sensitive: returns ssi_income only for the
    ("yearly", ["sSI"]) call, 0 otherwise.
    """
    member = Mock()
    member.age = age
    member.disabled = disabled
    member.long_term_disability = long_term_disability
    member.calc_gross_income = Mock(side_effect=lambda period, types: ssi_income if types == ["sSI"] else 0)
    return member


def make_calculator(household_assets=0, has_ssi=False, members=None, married=False):
    """Create a KsKancareHcbs calculator with a mocked screen and program.

    `married=True` makes the head's is_married() report a spouse, which exercises
    the married-applicant path (asset test not applied).
    """
    mock_program = Mock()

    mock_screen = Mock()
    mock_screen.household_assets = household_assets
    mock_screen.has_ssi = has_ssi
    if members is None:
        members = [make_member()]
    mock_screen.household_members.all = Mock(return_value=members)

    # get_head().is_married() drives the married-applicant asset-test bypass.
    head = members[0]
    head.is_married = Mock(return_value={"is_married": married, "married_to": (members[1] if married and len(members) > 1 else None)})
    mock_screen.get_head = Mock(return_value=head)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return KsKancareHcbs(mock_screen, mock_program, {}, mock_missing_deps)


def run_household(calc, members=None):
    """Run member + household eligibility the way the base eligible() does."""
    if members is None:
        members = calc.screen.household_members.all()
    e = Eligibility()
    one_eligible = False
    for member in members:
        from programs.programs.calc import MemberEligibility

        me = MemberEligibility(member)
        calc.member_eligible(me)
        e.add_member_eligibility(me)
        if me.eligible:
            one_eligible = True
    e.condition(one_eligible)
    calc.household_eligible(e)
    return e


class TestKsKancareHcbsClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(KsKancareHcbs, ProgramCalculator))

    def test_is_registered_in_ks_calculators(self):
        self.assertIn("ks_kancare_hcbs", ks_calculators)
        self.assertEqual(ks_calculators["ks_kancare_hcbs"], KsKancareHcbs)

    def test_asset_limit_is_2000(self):
        self.assertEqual(KsKancareHcbs.asset_limit, 2_000)

    def test_amount_is_35000(self):
        self.assertEqual(KsKancareHcbs.amount, 35_000)

    def test_dependencies_include_household_assets(self):
        self.assertIn("household_assets", KsKancareHcbs.dependencies)


class TestKsKancareHcbsAssetGate(TestCase):
    """The asset limit is the only hard screener-testable gate (inclusive <= $2,000)."""

    def test_assets_under_limit_eligible(self):
        e = run_household(make_calculator(household_assets=1_200))
        self.assertTrue(e.eligible)

    def test_assets_exactly_at_limit_eligible(self):
        """Scenario 5: $2,000 exactly is eligible (boundary is inclusive)."""
        e = run_household(make_calculator(household_assets=2_000))
        self.assertTrue(e.eligible)

    def test_assets_one_dollar_over_limit_ineligible(self):
        """Scenario 6: $2,001 is ineligible (strict boundary, off-by-one check)."""
        e = run_household(make_calculator(household_assets=2_001))
        self.assertFalse(e.eligible)

    def test_assets_well_over_limit_ineligible(self):
        """Scenario 2: $8,500 is ineligible — primary exclusion."""
        e = run_household(make_calculator(household_assets=8_500))
        self.assertFalse(e.eligible)

    def test_assets_none_treated_as_zero_eligible(self):
        e = run_household(make_calculator(household_assets=None))
        self.assertTrue(e.eligible)


class TestKsKancareHcbsSsiBypass(TestCase):
    """SSI confers automatic KanCare financial eligibility, bypassing the asset test."""

    def test_ssi_checkbox_bypasses_over_limit_assets(self):
        """Scenario 4: SSI recipient with assets above $2,000 is still eligible."""
        e = run_household(make_calculator(household_assets=3_500, has_ssi=True))
        self.assertTrue(e.eligible)

    def test_ssi_income_stream_bypasses_over_limit_assets(self):
        member = make_member(age=55, ssi_income=943 * 12)
        e = run_household(make_calculator(household_assets=3_500, members=[member]))
        self.assertTrue(e.eligible)

    def test_no_ssi_and_over_limit_assets_ineligible(self):
        member = make_member(age=55, ssi_income=0)
        e = run_household(make_calculator(household_assets=3_500, has_ssi=False, members=[member]))
        self.assertFalse(e.eligible)

    def test_ssi_uses_ssi_token_not_all(self):
        """Regression: SSI detection must query the ["sSI"] income token.

        The member mock returns income only for ("yearly", ["sSI"]). If the
        calculator queried a different token, has_ssi would be False and the
        over-limit assets would make the household ineligible.
        """
        member = make_member(age=40, ssi_income=500)
        e = run_household(make_calculator(household_assets=9_999, members=[member]))
        self.assertTrue(e.eligible)


class TestKsKancareHcbsIncomeNotDisqualifying(TestCase):
    """Income never disqualifies — only the asset test gates (per spec criterion 2)."""

    def test_high_income_low_assets_eligible(self):
        """Scenario 3: $3,800/month income (above $2,982 cost-share threshold) still eligible."""
        member = make_member(age=50)
        # Income is not even read by the calculator; assets under limit -> eligible.
        e = run_household(make_calculator(household_assets=500, members=[member]))
        self.assertTrue(e.eligible)


class TestKsKancareHcbsNoAgeOrDisabilityGate(TestCase):
    """Age and disability flags are informational only, never gates."""

    def test_no_disability_flags_still_eligible(self):
        """Scenario 7: disabled=False, long_term_disability=False, still surfaced."""
        member = make_member(age=30, disabled=False, long_term_disability=False)
        e = run_household(make_calculator(household_assets=600, members=[member]))
        self.assertTrue(e.eligible)

    def test_young_child_in_household_eligible(self):
        """Scenario 9: household with a young child, no disability flags, under asset limit."""
        adult = make_member(age=32, disabled=False)
        child = make_member(age=4, disabled=False)
        e = run_household(make_calculator(household_assets=500, members=[adult, child]))
        self.assertTrue(e.eligible)

    def test_working_age_adult_pd_target_eligible(self):
        """Scenario 10: age 28 PD-target adult, low assets, eligible regardless of age."""
        member = make_member(age=28, disabled=True, long_term_disability=True)
        e = run_household(make_calculator(household_assets=900, members=[member]))
        self.assertTrue(e.eligible)


class TestKsKancareHcbsMarriedAssets(TestCase):
    """Married applicants are not asset-gated (spousal-split data gap, criterion 3).

    The screener captures one combined household-assets total and cannot apply
    spousal-impoverishment protections, so the $2,000 single limit is not applied
    when a spouse/partner is present.
    """

    def test_married_assets_over_limit_eligible(self):
        """Scenario 8: married couple, combined $2,500 > $2,000 single limit -> eligible (not asset-gated)."""
        m1 = make_member(age=68, disabled=True)
        m2 = make_member(age=65, disabled=True)
        e = run_household(make_calculator(household_assets=2_500, members=[m1, m2], married=True))
        self.assertTrue(e.eligible)

    def test_married_high_assets_still_eligible(self):
        """A married couple well over the single limit is still not asset-gated."""
        m1 = make_member(age=68, disabled=True)
        m2 = make_member(age=65, disabled=True)
        e = run_household(make_calculator(household_assets=50_000, members=[m1, m2], married=True))
        self.assertTrue(e.eligible)

    def test_nonspousal_multimember_over_limit_ineligible(self):
        """Non-spousal multi-member household (e.g. parent + adult child) is still
        asset-gated on the combined total — only married applicants bypass."""
        m1 = make_member(age=70, disabled=True)
        m2 = make_member(age=40)
        e = run_household(make_calculator(household_assets=2_500, members=[m1, m2], married=False))
        self.assertFalse(e.eligible)


class TestKsKancareHcbsValue(TestCase):
    """Flat $35,000/year benefit value for eligible households."""

    def test_eligible_household_value_is_35000(self):
        calc = make_calculator(household_assets=1_200)
        e = run_household(calc)
        calc.value(e)
        self.assertEqual(e.value, 35_000)

    def test_ineligible_household_value_is_zero(self):
        calc = make_calculator(household_assets=8_500)
        e = run_household(calc)
        calc.value(e)
        self.assertEqual(e.value, 0)


class TestKsKancareHcbsEndToEnd(TestCase):
    """Exercise calc() end-to-end for eligible and ineligible paths."""

    def test_calc_eligible_path(self):
        """Scenario 1 golden path: age 72, low income, $1,200 assets -> eligible, $35,000."""
        member = make_member(age=72)
        calc = make_calculator(household_assets=1_200, members=[member])
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 35_000)

    def test_calc_ineligible_path(self):
        """Scenario 2: age 69, $8,500 assets -> ineligible."""
        member = make_member(age=69)
        calc = make_calculator(household_assets=8_500, members=[member])
        result = calc.calc()
        self.assertFalse(result.eligible)
