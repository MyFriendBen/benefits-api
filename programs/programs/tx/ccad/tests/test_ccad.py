"""
Unit tests for TxCcad calculator class.

Eligibility requirements:
- Age 65+ OR age 21+ with disability
- Household income <= 300% FPL OR categorically eligible:
  - SNAP or TANF (household-level, bypasses income test for any age-eligible member)
  - SSI income or Medicaid (individual-level, only the age-eligible member's own benefits count)
"""

from django.test import TestCase
from unittest.mock import Mock, MagicMock

from programs.programs.tx import tx_calculators
from programs.programs.tx.ccad.calculator import TxCcad
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility


def make_calculator(
    has_snap=False,
    has_tanf=False,
    household_income=0,
    household_size=1,
    fpl_limit=15000,
):
    """Create a TxCcad calculator with a mocked screen and program."""
    mock_program = Mock()
    mock_program.year.get_limit.return_value = fpl_limit

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.has_benefit = Mock(side_effect=lambda b: {"snap": has_snap, "tanf": has_tanf}.get(b, False))
    mock_screen.calc_gross_income = Mock(return_value=household_income)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return TxCcad(mock_screen, mock_program, {}, mock_missing_deps)


def make_member(age, disabled=False, long_term_disability=False, visually_impaired=False, ssi_income=0, medicaid=False):
    """Create a mock household member."""
    member = Mock()
    member.age = age
    member.disabled = disabled
    member.long_term_disability = long_term_disability
    member.visually_impaired = visually_impaired
    member.has_disability = Mock(return_value=disabled or long_term_disability or visually_impaired)
    member.calc_gross_income = Mock(return_value=ssi_income)
    member.has_benefit = Mock(side_effect=lambda b: medicaid if b == "medicaid" else False)
    return member


def make_eligible_member_e(member):
    """Create a passing MemberEligibility for use in household_eligible tests."""
    me = MemberEligibility(member)
    me.eligible = True
    return me


class TestTxCcadClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(TxCcad, ProgramCalculator))

    def test_is_registered_in_tx_calculators(self):
        self.assertIn("tx_ccad", tx_calculators)
        self.assertEqual(tx_calculators["tx_ccad"], TxCcad)

    def test_min_age_is_65(self):
        self.assertEqual(TxCcad.min_age, 65)

    def test_min_age_disabled_is_21(self):
        self.assertEqual(TxCcad.min_age_disabled, 21)

    def test_fpl_percent_is_3(self):
        self.assertEqual(TxCcad.fpl_percent, 3)

    def test_amount_is_10000(self):
        self.assertEqual(TxCcad.amount, 10_000)


class TestTxCcadMemberEligibility(TestCase):
    """Tests for age and disability gate in member_eligible."""

    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_age_65_is_eligible(self):
        self.assertTrue(self._run(make_member(age=65)))

    def test_age_64_without_disability_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=64)))

    def test_age_21_with_disability_is_eligible(self):
        self.assertTrue(self._run(make_member(age=21, disabled=True)))

    def test_age_21_without_disability_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=21, disabled=False)))

    def test_age_20_with_disability_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=20, disabled=True)))

    def test_age_none_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=None)))

    def test_long_term_disability_qualifies_as_disability(self):
        self.assertTrue(self._run(make_member(age=21, long_term_disability=True)))

    def test_visually_impaired_qualifies_as_disability(self):
        self.assertTrue(self._run(make_member(age=21, visually_impaired=True)))

    def test_age_80_no_disability_required(self):
        self.assertTrue(self._run(make_member(age=80, disabled=False)))


class TestTxCcadHouseholdIncomeEligibility(TestCase):
    """Tests for the income gate — 300% FPL with no categorical bypass."""

    def _run(self, household_income, fpl_limit=15000):
        # fpl_percent=3, so income_limit = 3 * fpl_limit
        calc = make_calculator(household_income=household_income, fpl_limit=fpl_limit)
        member = make_member(age=68)
        e = Eligibility()
        e.add_member_eligibility(make_eligible_member_e(member))
        calc.household_eligible(e)
        return e.eligible

    def test_income_below_300_fpl_is_eligible(self):
        self.assertTrue(self._run(household_income=10000, fpl_limit=5000))  # limit=15000, income=10000

    def test_income_exactly_at_300_fpl_is_eligible(self):
        self.assertTrue(self._run(household_income=15000, fpl_limit=5000))  # limit=15000, income=15000

    def test_income_above_300_fpl_is_ineligible(self):
        self.assertFalse(self._run(household_income=15001, fpl_limit=5000))  # limit=15000, income=15001


class TestTxCcadSnapTanfCategoricalEligibility(TestCase):
    """SNAP and TANF are household-level and bypass the income test."""

    def _run(self, has_snap=False, has_tanf=False, household_income=99999, fpl_limit=5000):
        calc = make_calculator(has_snap=has_snap, has_tanf=has_tanf, household_income=household_income, fpl_limit=fpl_limit)
        member = make_member(age=68)
        e = Eligibility()
        e.add_member_eligibility(make_eligible_member_e(member))
        calc.household_eligible(e)
        return e.eligible

    def test_snap_bypasses_income_test(self):
        self.assertTrue(self._run(has_snap=True))

    def test_tanf_bypasses_income_test(self):
        self.assertTrue(self._run(has_tanf=True))

    def test_no_categorical_and_high_income_is_ineligible(self):
        self.assertFalse(self._run())


class TestTxCcadMedicaidSsiCategoricalEligibility(TestCase):
    """SSI and Medicaid only count for the age-eligible member — not other household members."""

    def _make_calc_with_members(self, eligible_members, household_income=99999, fpl_limit=5000):
        calc = make_calculator(household_income=household_income, fpl_limit=fpl_limit)
        e = Eligibility()
        for member in eligible_members:
            e.add_member_eligibility(make_eligible_member_e(member))
        calc.household_eligible(e)
        return e.eligible

    def test_medicaid_on_eligible_member_bypasses_income(self):
        member = make_member(age=68, medicaid=True)
        self.assertTrue(self._make_calc_with_members([member]))

    def test_ssi_income_on_eligible_member_bypasses_income(self):
        member = make_member(age=68, ssi_income=943)
        self.assertTrue(self._make_calc_with_members([member]))

    def test_medicaid_on_ineligible_member_does_not_bypass_income(self):
        """A 35-year-old with Medicaid should not grant categorical eligibility to the age-eligible member."""
        age_eligible = make_member(age=68, medicaid=False)
        ineligible_with_medicaid = make_member(age=35, medicaid=True)

        calc = make_calculator(household_income=99999, fpl_limit=5000)
        e = Eligibility()
        e.add_member_eligibility(make_eligible_member_e(age_eligible))
        # ineligible member (age=35 fails member_eligible) — mark as not eligible
        ineligible_me = MemberEligibility(ineligible_with_medicaid)
        ineligible_me.eligible = False
        e.add_member_eligibility(ineligible_me)
        calc.household_eligible(e)
        self.assertFalse(e.eligible)

    def test_no_ssi_or_medicaid_and_high_income_is_ineligible(self):
        member = make_member(age=68, ssi_income=0, medicaid=False)
        self.assertFalse(self._make_calc_with_members([member]))
