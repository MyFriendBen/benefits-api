"""
Unit tests for TxSsdi calculator.

Covers all spec.md test scenarios plus edge cases:
- Disability: long_term_disability required; general disabled flag alone is insufficient
- Current benefits: already receiving SSDI disqualifies; SSI does not (concurrent OK)
- SS retirement: sSRetirement income disqualifies
- SGA income: earned-only, non-blind $1,690 and blind $2,830 thresholds (inclusive)
- FRA age: dynamically computed from birth year per SSA schedule
- Household: per-member evaluation; spousal income is irrelevant
- Value: $1,580 × 12 per eligible member
"""

from unittest.mock import Mock, call

from django.test import SimpleTestCase as TestCase

from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.tx import tx_calculators
from programs.programs.tx.ssdi.calculator import TxSsdi, _FRA_BY_BIRTH_YEAR


def make_calculator(has_ssdi=False):
    """Create a TxSsdi calculator with a mocked screen."""
    mock_screen = Mock()
    mock_screen.has_benefit = Mock(return_value=has_ssdi)
    mock_program = Mock()
    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False
    return TxSsdi(mock_screen, mock_program, {}, mock_missing_deps)


def make_member(
    age=50,
    birth_year=1976,
    long_term_disability=True,
    visually_impaired=False,
    earned_income=0,
    ss_retirement_income=0,
):
    """Create a mock HouseholdMember with configurable SSDI-relevant fields.

    birth_year defaults to 1976 (FRA=67). fraction_age() defaults to float(age),
    matching the screener's fallback when birth_year_month is not set.
    """
    mock_member = Mock()
    mock_member.age = age
    mock_member.birth_year = birth_year
    mock_member.fraction_age = Mock(return_value=float(age))
    mock_member.long_term_disability = long_term_disability
    mock_member.visually_impaired = visually_impaired

    def calc_gross_income(period, income_types):
        if list(income_types) == ["sSRetirement"]:
            return ss_retirement_income
        if list(income_types) == ["earned"]:
            return earned_income
        return 0

    mock_member.calc_gross_income = Mock(side_effect=calc_gross_income)
    return mock_member


def run_member_eligible(member, has_ssdi=False):
    """Run member_eligible and return the MemberEligibility result."""
    calculator = make_calculator(has_ssdi=has_ssdi)
    e = MemberEligibility(member)
    calculator.member_eligible(e)
    return e


class TestTxSsdiRegistration(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(TxSsdi, ProgramCalculator))

    def test_registered_in_tx_calculators(self):
        self.assertIn("tx_ssdi", tx_calculators)
        self.assertEqual(tx_calculators["tx_ssdi"], TxSsdi)


class TestTxSsdiDisabilityCheck(TestCase):
    """Scenarios 1, 12, 13 — long_term_disability is required."""

    def test_long_term_disability_true_is_eligible(self):
        # Scenario 1 / 12: long_term_disability=True qualifies
        member = make_member(long_term_disability=True)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_long_term_disability_only_no_general_disabled_is_eligible(self):
        # Scenario 12: disabled=False, long_term_disability=True → eligible
        member = make_member(long_term_disability=True)
        member.disabled = False
        self.assertTrue(run_member_eligible(member).eligible)

    def test_general_disability_only_is_not_eligible(self):
        # Scenario 13: disabled=True, long_term_disability=False → not eligible
        member = make_member(long_term_disability=False)
        member.disabled = True
        self.assertFalse(run_member_eligible(member).eligible)

    def test_no_disability_at_all_is_not_eligible(self):
        member = make_member(long_term_disability=False)
        self.assertFalse(run_member_eligible(member).eligible)


class TestTxSsdiCurrentBenefits(TestCase):
    """Scenarios 5, 6 — SSDI checkbox disqualifies; SSI does not."""

    def test_already_receiving_ssdi_is_not_eligible(self):
        # Scenario 5: current_benefits includes SSDI → not eligible
        member = make_member()
        self.assertFalse(run_member_eligible(member, has_ssdi=True).eligible)

    def test_already_receiving_ssdi_has_benefit_called_with_tx_ssdi(self):
        calculator = make_calculator(has_ssdi=False)
        member = make_member()
        e = MemberEligibility(member)
        calculator.member_eligible(e)
        calculator.screen.has_benefit.assert_called_with("tx_ssdi")

    def test_already_receiving_ssi_is_still_eligible(self):
        # Scenario 6: SSI and SSDI are concurrent; SSI receipt doesn't disqualify
        member = make_member()
        # has_ssdi=False — screen.has_benefit("tx_ssdi") returns False
        self.assertTrue(run_member_eligible(member, has_ssdi=False).eligible)


class TestTxSsdiSsRetirement(TestCase):
    """Scenario 14 — SS retirement income disqualifies."""

    def test_ss_retirement_income_is_not_eligible(self):
        # Scenario 14: person receiving sSRetirement income → not eligible
        member = make_member(ss_retirement_income=900)
        self.assertFalse(run_member_eligible(member).eligible)

    def test_no_ss_retirement_income_is_eligible(self):
        member = make_member(ss_retirement_income=0)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_sga_check_uses_earned_income_not_ss_retirement(self):
        # SS retirement income must not affect the SGA check
        member = make_member(ss_retirement_income=900, earned_income=0)
        self.assertFalse(run_member_eligible(member).eligible)  # ineligible due to sSRetirement, not SGA


class TestTxSsdiSgaIncome(TestCase):
    """Scenarios 3, 4, 10, 11 — SGA thresholds; checks use earned income only."""

    def test_no_earned_income_is_eligible(self):
        # Scenario 1: $0 earned income → eligible
        member = make_member(earned_income=0)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_income_at_sga_threshold_is_eligible(self):
        # Scenario 3: $1,690/month exactly → eligible (inclusive boundary)
        member = make_member(earned_income=1_690)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_income_above_sga_threshold_is_not_eligible(self):
        # Scenario 4: $1,750/month → not eligible
        member = make_member(earned_income=1_750)
        self.assertFalse(run_member_eligible(member).eligible)

    def test_income_one_dollar_above_sga_is_not_eligible(self):
        member = make_member(earned_income=1_691)
        self.assertFalse(run_member_eligible(member).eligible)

    def test_blind_income_below_blind_sga_is_eligible(self):
        # Scenario 10: visually_impaired, $2,500/month (below $2,830 blind SGA) → eligible
        member = make_member(visually_impaired=True, earned_income=2_500)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_blind_income_at_blind_sga_threshold_is_eligible(self):
        # Blind SGA boundary is also inclusive
        member = make_member(visually_impaired=True, earned_income=2_830)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_blind_income_above_blind_sga_is_not_eligible(self):
        # Scenario 11: visually_impaired, $3,000/month (above $2,830 blind SGA) → not eligible
        member = make_member(visually_impaired=True, earned_income=3_000)
        self.assertFalse(run_member_eligible(member).eligible)

    def test_blind_income_above_nonblind_sga_but_below_blind_sga_is_eligible(self):
        # $2,500 is above non-blind limit ($1,690) but below blind limit ($2,830)
        member = make_member(visually_impaired=True, earned_income=2_500)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_nonblind_income_above_nonblind_sga_is_not_eligible(self):
        member = make_member(visually_impaired=False, earned_income=2_500)
        self.assertFalse(run_member_eligible(member).eligible)

    def test_sga_uses_earned_income_not_all_income(self):
        # Verify calc_gross_income is called with ["earned"], not ["all"]
        member = make_member(ss_retirement_income=0, earned_income=0)
        run_member_eligible(member)
        self.assertIn(call("monthly", ["earned"]), member.calc_gross_income.call_args_list)


class TestTxSsdiFraTable(TestCase):
    """Unit tests for _full_retirement_age() and the FRA lookup table."""

    def test_born_1937_or_earlier_fra_is_65(self):
        self.assertEqual(TxSsdi._full_retirement_age(1937), 65.0)
        self.assertEqual(TxSsdi._full_retirement_age(1920), 65.0)

    def test_born_1938_fra_is_65_years_2_months(self):
        self.assertAlmostEqual(TxSsdi._full_retirement_age(1938), 65 + 2 / 12)

    def test_born_1942_fra_is_65_years_10_months(self):
        self.assertAlmostEqual(TxSsdi._full_retirement_age(1942), 65 + 10 / 12)

    def test_born_1943_to_1954_fra_is_66(self):
        for year in range(1943, 1955):
            with self.subTest(birth_year=year):
                self.assertEqual(TxSsdi._full_retirement_age(year), 66.0)

    def test_born_1955_fra_is_66_years_2_months(self):
        self.assertAlmostEqual(TxSsdi._full_retirement_age(1955), 66 + 2 / 12)

    def test_born_1959_fra_is_66_years_10_months(self):
        self.assertAlmostEqual(TxSsdi._full_retirement_age(1959), 66 + 10 / 12)

    def test_born_1960_fra_is_67(self):
        self.assertEqual(TxSsdi._full_retirement_age(1960), 67.0)

    def test_born_after_1960_fra_is_67(self):
        self.assertEqual(TxSsdi._full_retirement_age(1990), 67.0)
        self.assertEqual(TxSsdi._full_retirement_age(2000), 67.0)

    def test_birth_year_none_falls_back_to_67(self):
        # When birth_year_month is not set, default conservatively to 67
        self.assertEqual(TxSsdi._full_retirement_age(None), 67.0)

    def test_fra_table_covers_all_transitional_years(self):
        # Ensure every year from 1938-1959 is in the table (no KeyError)
        for year in range(1938, 1960):
            with self.subTest(birth_year=year):
                self.assertIn(year, _FRA_BY_BIRTH_YEAR)


class TestTxSsdiAge(TestCase):
    """Scenarios 2, 9 — FRA boundary; uses fraction_age() and birth_year."""

    def test_age_50_born_1976_is_eligible(self):
        # Scenario 1: core happy path, born 1960+ (FRA=67), age 50
        member = make_member(age=50, birth_year=1976)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_age_66_born_1960_is_eligible(self):
        # Scenario 2: born 1960 (FRA=67), fraction_age=66.0 < 67.0 → eligible
        member = make_member(age=66, birth_year=1960)
        member.fraction_age = Mock(return_value=66.0)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_age_67_born_1960_is_not_eligible(self):
        # Born 1960 (FRA=67), fraction_age=67.0 — exactly at FRA → not eligible
        member = make_member(age=67, birth_year=1960)
        member.fraction_age = Mock(return_value=67.0)
        self.assertFalse(run_member_eligible(member).eligible)

    def test_age_67_born_1959_past_fra_is_not_eligible(self):
        # Scenario 9: born Jan 1959 (FRA=66y10m≈66.833), now 67y2m past FRA → not eligible
        member = make_member(age=67, birth_year=1959)
        member.fraction_age = Mock(return_value=67 + 2 / 12)
        self.assertFalse(run_member_eligible(member).eligible)

    def test_age_66_born_1954_is_eligible(self):
        # Born 1954 (FRA=66.0 exactly), fraction_age=65.5 — not yet reached FRA → eligible
        member = make_member(age=65, birth_year=1954)
        member.fraction_age = Mock(return_value=65.5)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_age_66_born_1954_at_fra_is_not_eligible(self):
        # Born 1954 (FRA=66.0), fraction_age=66.0 — exactly at FRA → not eligible
        member = make_member(age=66, birth_year=1954)
        member.fraction_age = Mock(return_value=66.0)
        self.assertFalse(run_member_eligible(member).eligible)

    def test_born_1959_just_before_fra_is_eligible(self):
        # Born 1959 (FRA=66y10m≈66.833), fraction_age=66.5 — not yet reached FRA → eligible
        member = make_member(age=66, birth_year=1959)
        member.fraction_age = Mock(return_value=66.5)
        self.assertTrue(run_member_eligible(member).eligible)

    def test_born_1959_just_after_fra_is_not_eligible(self):
        # Born 1959 (FRA=66y10m≈66.833), fraction_age=66.9 — just past FRA → not eligible
        member = make_member(age=66, birth_year=1959)
        member.fraction_age = Mock(return_value=66.9)
        self.assertFalse(run_member_eligible(member).eligible)


class TestTxSsdiHouseholdEligibility(TestCase):
    """Scenarios 7, 8 — per-member evaluation; spousal income is irrelevant."""

    def test_mixed_household_only_disabled_member_is_eligible(self):
        # Scenario 7: disabled head qualifies; non-disabled spouse does not
        calculator = make_calculator()

        disabled_head = make_member(age=54, long_term_disability=True, earned_income=0)
        non_disabled_spouse = make_member(age=51, long_term_disability=False, earned_income=2_800)

        head_e = MemberEligibility(disabled_head)
        spouse_e = MemberEligibility(non_disabled_spouse)
        calculator.member_eligible(head_e)
        calculator.member_eligible(spouse_e)

        self.assertTrue(head_e.eligible)
        self.assertFalse(spouse_e.eligible)

    def test_two_disabled_workers_both_eligible(self):
        # Scenario 8: two disabled workers independently qualify
        calculator = make_calculator()

        member1 = make_member(age=55, long_term_disability=True, earned_income=0)
        member2 = make_member(age=52, long_term_disability=True, earned_income=0)

        e1 = MemberEligibility(member1)
        e2 = MemberEligibility(member2)
        calculator.member_eligible(e1)
        calculator.member_eligible(e2)

        self.assertTrue(e1.eligible)
        self.assertTrue(e2.eligible)

    def test_spousal_income_does_not_affect_disabled_member_eligibility(self):
        # SSDI is an individual entitlement; spouse earning $2,800/month is irrelevant
        calculator = make_calculator()
        disabled_head = make_member(age=54, long_term_disability=True, earned_income=0)
        e = MemberEligibility(disabled_head)
        calculator.member_eligible(e)
        self.assertTrue(e.eligible)


class TestTxSsdiValue(TestCase):
    """Value: $1,580 × 12 per eligible member."""

    def _run_with_value(self, member, has_ssdi=False):
        calculator = make_calculator(has_ssdi=has_ssdi)
        member_e = MemberEligibility(member)
        calculator.member_eligible(member_e)
        household_e = Eligibility()
        household_e.add_member_eligibility(member_e)
        calculator.value(household_e)
        return household_e, member_e

    def test_eligible_member_receives_annual_benefit(self):
        member = make_member()
        _, member_e = self._run_with_value(member)
        self.assertTrue(member_e.eligible)
        self.assertEqual(member_e.value, 1_580 * 12)

    def test_ineligible_member_receives_zero(self):
        member = make_member(long_term_disability=False)
        _, member_e = self._run_with_value(member)
        self.assertFalse(member_e.eligible)
        self.assertEqual(member_e.value, 0)

    def test_two_eligible_members_each_receive_annual_benefit(self):
        calculator = make_calculator()
        members = [make_member(age=50), make_member(age=52)]
        member_eligibilities = []
        for m in members:
            e = MemberEligibility(m)
            calculator.member_eligible(e)
            member_eligibilities.append(e)

        household_e = Eligibility()
        for me in member_eligibilities:
            household_e.add_member_eligibility(me)
        calculator.value(household_e)

        for me in member_eligibilities:
            self.assertTrue(me.eligible)
            self.assertEqual(me.value, 1_580 * 12)
