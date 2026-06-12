"""
Unit tests for TxFpp (Texas Family Planning Program) custom calculator.

Eligibility:
- Age 64 or younger (no minimum age)
- Not enrolled in full Medicaid (Emergency Medicaid and other coverage are OK)
- Household income <= 250% FPL, OR §4140 adjunctive bypass (SNAP / WIC / CHIP)

Benefit value: $266.84/year per eligible member.
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.tx import tx_calculators
from programs.programs.tx.fpp.calculator import TxFpp
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility


def make_member(age=30, medicaid=False, emergency_medicaid=False, employer=False, none=True):
    """Mock a household member with an insurance object."""
    member = Mock()
    member.age = age

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
    current_benefits=None,
    has_chp=False,
    household_income=0,
    household_size=1,
    fpl_limit=15_000,
    members=None,
):
    """Create a TxFpp calculator with a mocked screen and program.

    The §4140 adjunctive bypass reads enrollment the way a real screen exposes it:
    SNAP/WIC from the CurrentBenefit join table via has_benefit(), and CHIP from
    per-member insurance via has_insurance_types(("chp",)). The mocks below mirror
    those methods rather than the legacy has_snap/has_wic/has_chp columns, which the
    serializer no longer populates (MFB-720) — so a regression back to those dead
    columns would fail these tests.

    Args:
        current_benefits: name_abbreviated strings the household already receives,
            as written to the CurrentBenefit join table — e.g. ["tx_snap", "tx_wic"].
            Drives has_benefit(). Note tx_chip is never a current benefit (it's a
            PolicyEngine eligibility program), so passing it here is a no-op; use
            has_chp for CHIP.
        has_chp: whether a household member has CHIP coverage — a per-member
            insurance flag, read via has_insurance_types(("chp",)), not a current
            benefit.
    """
    mock_program = Mock()
    mock_program.year.get_limit.return_value = fpl_limit

    benefits = set(current_benefits or [])

    mock_screen = Mock()
    mock_screen.has_benefit = Mock(side_effect=lambda name_abbreviated: name_abbreviated in benefits)
    mock_screen.has_insurance_types = Mock(side_effect=lambda types, strict=True: has_chp and "chp" in types)
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(return_value=household_income)
    mock_screen.household_members.all = Mock(return_value=members if members is not None else [])

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return TxFpp(mock_screen, mock_program, {}, mock_missing_deps)


def add_eligible_member(e, member):
    me = MemberEligibility(member)
    me.eligible = True
    e.add_member_eligibility(me)
    return me


class TestTxFppClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(TxFpp, ProgramCalculator))

    def test_is_registered_in_tx_calculators(self):
        self.assertIn("tx_fpp", tx_calculators)
        self.assertEqual(tx_calculators["tx_fpp"], TxFpp)

    def test_max_age_is_64(self):
        self.assertEqual(TxFpp.max_age, 64)

    def test_fpl_percent_is_250(self):
        self.assertEqual(TxFpp.fpl_percent, 2.5)

    def test_member_amount_is_annual_benefit(self):
        self.assertAlmostEqual(TxFpp.member_amount, 266.84)


class TestTxFppMemberEligibility(TestCase):
    """Age and insurance gate in member_eligible."""

    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_age_64_is_eligible(self):
        self.assertTrue(self._run(make_member(age=64)))

    def test_age_65_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=65)))

    def test_age_none_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=None)))

    def test_no_minimum_age_young_child_is_age_eligible(self):
        """No minimum age — HHS states only '64 or younger'."""
        self.assertTrue(self._run(make_member(age=5)))

    def test_uninsured_is_eligible(self):
        self.assertTrue(self._run(make_member(age=30, none=True)))

    def test_full_medicaid_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=30, none=False, medicaid=True)))

    def test_emergency_medicaid_remains_eligible(self):
        """Emergency Medicaid is underinsured (§4100) — not excluded."""
        self.assertTrue(self._run(make_member(age=30, none=False, emergency_medicaid=True)))

    def test_employer_insurance_does_not_disqualify(self):
        """Medicaid-only exclusion — other coverage does not disqualify (§4200)."""
        self.assertTrue(self._run(make_member(age=30, none=False, employer=True)))


class TestTxFppHouseholdIncome(TestCase):
    """Income gate — 250% FPL with no adjunctive bypass."""

    def _run(self, household_income, fpl_limit=15_000):
        # fpl_percent=2.5, so income_limit = int(2.5 * fpl_limit)
        calc = make_calculator(household_income=household_income, fpl_limit=fpl_limit)
        e = Eligibility()
        add_eligible_member(e, make_member(age=30))
        calc.household_eligible(e)
        return e.eligible

    def test_income_below_250_fpl_is_eligible(self):
        self.assertTrue(self._run(household_income=20_000, fpl_limit=15_000))  # limit 37,500

    def test_income_exactly_at_250_fpl_is_eligible(self):
        self.assertTrue(self._run(household_income=37_500, fpl_limit=15_000))  # limit 37,500

    def test_income_above_250_fpl_is_ineligible(self):
        self.assertFalse(self._run(household_income=37_501, fpl_limit=15_000))  # limit 37,500


class TestTxFppAdjunctiveBypass(TestCase):
    """§4140 — SNAP / WIC / CHIP enrollment bypasses the income test."""

    def _run(self, current_benefits=None, has_chp=False, household_income=99_999, fpl_limit=15_000):
        calc = make_calculator(
            current_benefits=current_benefits,
            has_chp=has_chp,
            household_income=household_income,
            fpl_limit=fpl_limit,
        )
        e = Eligibility()
        add_eligible_member(e, make_member(age=35))
        calc.household_eligible(e)
        return e.eligible

    def test_snap_bypasses_income_test(self):
        self.assertTrue(self._run(current_benefits=["tx_snap"]))

    def test_wic_bypasses_income_test(self):
        self.assertTrue(self._run(current_benefits=["tx_wic"]))

    def test_chip_bypasses_income_test(self):
        self.assertTrue(self._run(has_chp=True))

    def test_no_bypass_and_high_income_is_ineligible(self):
        self.assertFalse(self._run())


class TestTxFppValue(TestCase):
    """Benefit value — $266.84 per eligible member, summed across members."""

    def test_member_value_is_annual_benefit(self):
        calc = make_calculator()
        self.assertAlmostEqual(calc.member_value(make_member(age=30)), 266.84)

    def test_single_eligible_member_value(self):
        member = make_member(age=30)
        calc = make_calculator(household_income=10_000, fpl_limit=15_000, members=[member])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, 266.84)

    def test_two_eligible_members_value_sums(self):
        members = [make_member(age=55), make_member(age=30)]
        calc = make_calculator(household_income=20_000, fpl_limit=15_000, members=members)
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, 533.68)

    def test_medicaid_member_excluded_from_value(self):
        """A Medicaid member does not count; only the eligible member contributes value."""
        eligible = make_member(age=32, none=True)
        medicaid_member = make_member(age=8, none=False, medicaid=True)
        calc = make_calculator(household_income=20_000, fpl_limit=15_000, members=[eligible, medicaid_member])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, 266.84)


class TestTxFppIntegration(TestCase):
    """End-to-end calc() for the main ineligible paths."""

    def test_over_age_household_is_ineligible(self):
        member = make_member(age=70)
        calc = make_calculator(household_income=10_000, fpl_limit=15_000, members=[member])
        e = calc.calc()
        self.assertFalse(e.eligible)

    def test_over_income_no_bypass_is_ineligible(self):
        member = make_member(age=30)
        calc = make_calculator(household_income=99_999, fpl_limit=15_000, members=[member])
        e = calc.calc()
        self.assertFalse(e.eligible)
