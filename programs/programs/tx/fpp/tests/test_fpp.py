"""
Unit tests for TxFpp (Texas Family Planning Program) custom calculator.

Eligibility:
- Age 64 or younger (no minimum age)
- Not enrolled in full Medicaid (Emergency Medicaid and other coverage are OK)
- Countable income <= 250% FPL, OR §4140 adjunctive bypass (SNAP / WIC / CHIP)

Countable income mirrors PolicyEngine's gov.states.tx.fpp model at the version we serve
(policyengine-us 1.768.1): under-18 earnings are exempt, child support paid is deducted,
and child support received counts only above a monthly disregard. PE is treated as the
source of truth (not verified against 1 TAC §382.109 / the FPP Policy Manual).

Benefit value: $266.84/year per eligible member.
"""

from django.test import TestCase
from unittest.mock import Mock

from programs.programs.tx import tx_calculators
from programs.programs.tx.fpp.calculator import TxFpp
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility


def make_member(age=30, medicaid=False, emergency_medicaid=False, employer=False, none=True, earned=0):
    """Mock a household member with an insurance object and (optionally) earned income.

    `earned` is what the member's own `calc_gross_income(..., ["earned"])` returns — used by
    `_countable_income`, which exempts the earnings of members under `child_age_threshold`.
    """
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
    member.calc_gross_income = Mock(side_effect=lambda freq, types, exclude=[]: earned if "earned" in types else 0)
    return member


def make_calculator(
    current_benefits=None,
    has_chp=False,
    unearned=0,
    child_support_received=0,
    child_support_paid=0,
    household_size=1,
    fpl_limit=15_000,
    members=None,
):
    """Create a TxFpp calculator with a mocked screen and program.

    Income is modeled the way `_countable_income` reads it:
      - per-member earned income via each member's `calc_gross_income(["earned"])`
        (set with `make_member(earned=...)`),
      - `unearned` — screen-level unearned income excluding child support,
      - `child_support_received` — screen-level child support income,
      - `child_support_paid` — screen-level `childSupport` expense.

    The §4140 adjunctive bypass reads enrollment as a real screen exposes it: SNAP/WIC from
    the CurrentBenefit join table via has_benefit(), CHIP from per-member insurance via
    has_insurance_types(("chp",)) — not the legacy has_snap/has_wic/has_chp columns.
    """
    mock_program = Mock()
    mock_program.year.get_limit.return_value = fpl_limit

    benefits = set(current_benefits or [])

    def _gross(freq, types, exclude=[]):
        if "unearned" in types:
            return unearned
        if "childSupport" in types:
            return child_support_received
        return 0

    mock_screen = Mock()
    mock_screen.has_benefit = Mock(side_effect=lambda name_abbreviated: name_abbreviated in benefits)
    mock_screen.has_insurance_types = Mock(side_effect=lambda types, strict=True: has_chp and "chp" in types)
    mock_screen.household_size = household_size
    mock_screen.calc_gross_income = Mock(side_effect=_gross)
    mock_screen.calc_expenses = Mock(
        side_effect=lambda freq, types: child_support_paid if "childSupport" in types else 0
    )
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

    def test_child_age_threshold_is_18(self):
        self.assertEqual(TxFpp.child_age_threshold, 18)

    def test_child_support_disregard_is_75_monthly(self):
        """Child-support-received disregard is $75/month (Texas FPP Policy Manual,
        Definition of Income Rev 24-2; PE gov.states.tx.fpp.income.child_support_disregard)."""
        self.assertEqual(TxFpp.child_support_received_disregard_monthly, 75)


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
    """Income gate — countable income vs 250% FPL, no adjunctive bypass."""

    def _run(self, unearned, fpl_limit=15_000):
        # fpl_percent=2.5, so income_limit = int(2.5 * fpl_limit) = 37,500 at fpl_limit 15,000
        calc = make_calculator(unearned=unearned, fpl_limit=fpl_limit)
        e = Eligibility()
        add_eligible_member(e, make_member(age=30))
        calc.household_eligible(e)
        return e.eligible

    def test_income_below_250_fpl_is_eligible(self):
        self.assertTrue(self._run(unearned=20_000))  # limit 37,500

    def test_income_exactly_at_250_fpl_is_eligible(self):
        self.assertTrue(self._run(unearned=37_500))

    def test_income_above_250_fpl_is_ineligible(self):
        self.assertFalse(self._run(unearned=37_501))


class TestTxFppCountableIncome(TestCase):
    """The three ways countable income mirrors PolicyEngine (vs a flat gross total)."""

    def _household_eligible(self, calc):
        e = Eligibility()
        add_eligible_member(e, make_member(age=30))
        calc.household_eligible(e)
        return e.eligible

    def test_minor_earnings_are_exempt(self):
        """A minor's earnings don't count; only the adult's $30k is countable (<= $37,500)."""
        adult = make_member(age=40, earned=30_000)
        minor = make_member(age=16, earned=15_000)  # would push total to $45k if counted
        calc = make_calculator(fpl_limit=15_000, members=[adult, minor])
        self.assertTrue(self._household_eligible(calc))
        self.assertEqual(calc._countable_income(), 30_000)

    def test_adult_earnings_are_counted(self):
        """Members at/over 18 are adults — both earners count ($45k > $37,500)."""
        a1 = make_member(age=40, earned=30_000)
        a2 = make_member(age=18, earned=15_000)
        calc = make_calculator(fpl_limit=15_000, members=[a1, a2])
        self.assertFalse(self._household_eligible(calc))
        self.assertEqual(calc._countable_income(), 45_000)

    def test_child_support_paid_is_deducted(self):
        """$40k unearned minus $5k child support paid = $35k countable (<= $37,500)."""
        calc = make_calculator(unearned=40_000, child_support_paid=5_000, fpl_limit=15_000)
        self.assertTrue(self._household_eligible(calc))
        self.assertEqual(calc._countable_income(), 35_000)

    def test_child_support_received_applies_75_monthly_disregard(self):
        """$75/mo ($900/yr) is disregarded, so $10k received counts as $9,100:
        $28k + $9,100 = $37,100 (<= $37,500), eligible."""
        calc = make_calculator(unearned=28_000, child_support_received=10_000, fpl_limit=15_000)
        self.assertTrue(self._household_eligible(calc))
        self.assertEqual(calc._countable_income(), 37_100)

    def test_child_support_received_below_disregard_fully_excluded(self):
        """Received child support at or under the annual disregard counts as $0:
        $600/yr (< $900 disregard) → fully excluded, so only the $37k unearned counts."""
        calc = make_calculator(unearned=37_000, child_support_received=600, fpl_limit=15_000)
        self.assertTrue(self._household_eligible(calc))
        self.assertEqual(calc._countable_income(), 37_000)

    def test_disregard_is_what_changes_the_result(self):
        """Without the disregard the same household would be over the limit — confirms the
        disregard drives the outcome. $28k + $10k = $38k > $37,500."""
        calc = make_calculator(unearned=28_000, child_support_received=10_000, fpl_limit=15_000)
        calc.child_support_received_disregard_monthly = 0
        self.assertFalse(self._household_eligible(calc))
        self.assertEqual(calc._countable_income(), 38_000)

    def test_countable_income_floored_at_zero(self):
        """Deductions cannot drive countable income negative."""
        calc = make_calculator(unearned=1_000, child_support_paid=5_000, fpl_limit=15_000)
        self.assertEqual(calc._countable_income(), 0)

    def test_member_with_unknown_age_earnings_excluded(self):
        """A member with no recorded age is not treated as an adult, so their earnings are
        excluded (can't confirm they're 18+)."""
        adult = make_member(age=40, earned=20_000)
        unknown_age = make_member(age=None, earned=15_000)
        calc = make_calculator(fpl_limit=15_000, members=[adult, unknown_age])
        self.assertEqual(calc._countable_income(), 20_000)

    def test_child_support_paid_and_received_combined(self):
        """Both child-support branches apply together: $20k unearned + ($10k received −
        $900 disregard) − $5k paid = $24,100."""
        calc = make_calculator(
            unearned=20_000, child_support_received=10_000, child_support_paid=5_000, fpl_limit=15_000
        )
        self.assertEqual(calc._countable_income(), 24_100)

    def test_countable_income_combines_all_components(self):
        """adult earned + unearned + disregarded child support − child support paid.
        $18k adult earned + $10k unearned + ($5k received − $900) − $2k paid = $30,100."""
        adult = make_member(age=30, earned=18_000)
        minor = make_member(age=10, earned=9_999)  # exempt
        calc = make_calculator(
            unearned=10_000,
            child_support_received=5_000,
            child_support_paid=2_000,
            fpl_limit=15_000,
            members=[adult, minor],
        )
        self.assertEqual(calc._countable_income(), 30_100)


class TestTxFppAdjunctiveBypass(TestCase):
    """§4140 — SNAP / WIC / CHIP enrollment bypasses the income test."""

    def _run(self, current_benefits=None, has_chp=False, unearned=99_999, fpl_limit=15_000):
        calc = make_calculator(
            current_benefits=current_benefits,
            has_chp=has_chp,
            unearned=unearned,
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

    def test_unprefixed_snap_does_not_bypass(self):
        """Only the TX-scoped name bypasses. A bare "snap"/"wic" (e.g. a regression to the
        legacy columns) must NOT trigger the §4140 bypass."""
        self.assertFalse(self._run(current_benefits=["snap"]))

    def test_unprefixed_wic_does_not_bypass(self):
        self.assertFalse(self._run(current_benefits=["wic"]))

    def test_tx_chip_current_benefit_does_not_bypass(self):
        """CHIP bypass comes from per-member insurance (has_insurance_types), not a current
        benefit — tx_chip is a PE eligibility program, never written to the join table."""
        self.assertFalse(self._run(current_benefits=["tx_chip"]))

    def test_bypass_does_not_rescue_household_with_no_eligible_member(self):
        """The bypass only waives the income test. A household whose only member is
        disqualified (full Medicaid) is still ineligible even while enrolled in SNAP."""
        member = make_member(age=30, none=False, medicaid=True)
        calc = make_calculator(current_benefits=["tx_snap"], unearned=99_999, members=[member])
        e = calc.calc()
        self.assertFalse(e.eligible)


class TestTxFppValue(TestCase):
    """Benefit value — $266.84 per eligible member, summed across members."""

    def test_member_value_is_annual_benefit(self):
        calc = make_calculator()
        self.assertAlmostEqual(calc.member_value(make_member(age=30)), 266.84)

    def test_single_eligible_member_value(self):
        member = make_member(age=30)
        calc = make_calculator(unearned=10_000, fpl_limit=15_000, members=[member])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, 266.84)

    def test_two_eligible_members_value_sums(self):
        members = [make_member(age=55), make_member(age=30)]
        calc = make_calculator(unearned=20_000, fpl_limit=15_000, members=members)
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, 533.68)

    def test_medicaid_member_excluded_from_value(self):
        """A Medicaid member does not count; only the eligible member contributes value."""
        eligible = make_member(age=32, none=True)
        medicaid_member = make_member(age=8, none=False, medicaid=True)
        calc = make_calculator(unearned=20_000, fpl_limit=15_000, members=[eligible, medicaid_member])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, 266.84)

    def test_over_age_member_excluded_from_value(self):
        """An over-64 member is not eligible and contributes no value; only the in-range
        member counts."""
        eligible = make_member(age=40, none=True)
        over_age = make_member(age=70, none=True)
        calc = make_calculator(unearned=20_000, fpl_limit=15_000, members=[eligible, over_age])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, 266.84)


class TestTxFppIntegration(TestCase):
    """End-to-end calc() for the main ineligible paths."""

    def test_over_age_household_is_ineligible(self):
        member = make_member(age=70)
        calc = make_calculator(unearned=10_000, fpl_limit=15_000, members=[member])
        e = calc.calc()
        self.assertFalse(e.eligible)

    def test_over_income_no_bypass_is_ineligible(self):
        member = make_member(age=30)
        calc = make_calculator(unearned=99_999, fpl_limit=15_000, members=[member])
        e = calc.calc()
        self.assertFalse(e.eligible)

    def test_working_minor_household_eligible_end_to_end(self):
        """The minor-earnings exemption flows through the full calc(): an adult earning
        $30k plus a 16-year-old earning $15k is income-eligible ($30k countable <= $37,500,
        the minor's earnings exempt). Both are eligible members (FPP has no minimum age),
        so the household value is 2 × $266.84 — the exemption affects the income test, not
        who counts as a beneficiary.
        """
        adult = make_member(age=40, earned=30_000, none=True)
        minor = make_member(age=16, earned=15_000, none=True)
        calc = make_calculator(fpl_limit=15_000, members=[adult, minor])
        e = calc.calc()
        self.assertTrue(e.eligible)
        self.assertAlmostEqual(e.value, 533.68)

    def test_working_minor_would_be_ineligible_if_counted(self):
        """Control for the above: if the minor's $15k earnings counted, the $45k total would
        exceed the $37,500 limit. Setting the threshold to 0 (no exemption) makes it so."""
        adult = make_member(age=40, earned=30_000, none=True)
        minor = make_member(age=16, earned=15_000, none=True)
        calc = make_calculator(fpl_limit=15_000, members=[adult, minor])
        calc.child_age_threshold = 0  # count everyone's earnings
        e = calc.calc()
        self.assertFalse(e.eligible)
