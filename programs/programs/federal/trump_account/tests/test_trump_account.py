"""
Unit tests for TrumpAccount calculator.

Tests the 530A ("Trump") Account calculator logic:
- Pilot window eligibility (Jan 2025 – Dec 2028) using birth_year_month
- Age ceiling (under 18)
- Pregnancy path: estimated due date (reference_date + 280 days) must fall in pilot window
- Value: $1,000 per eligible member
"""

from datetime import date, timedelta
from unittest.mock import Mock

from django.test import TestCase

from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.federal import federal_calculators
from programs.programs.federal.trump_account.calculator import TrumpAccount


def make_calculator(reference_date=None):
    """Create a TrumpAccount calculator with a mocked screen."""
    mock_screen = Mock()
    mock_screen.get_reference_date.return_value = reference_date or date(2026, 3, 11)
    mock_program = Mock()
    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False
    return TrumpAccount(mock_screen, mock_program, {}, mock_missing_deps)


def make_member(age=1, birth_year_month=None, pregnant=False):
    """Create a mock HouseholdMember."""
    mock_member = Mock()
    mock_member.age = age
    mock_member.birth_year_month = birth_year_month
    mock_member.pregnant = pregnant
    return mock_member


class TestTrumpAccountRegistration(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(TrumpAccount, ProgramCalculator))

    def test_registered_in_federal_calculators(self):
        self.assertIn("trump_account", federal_calculators)
        self.assertEqual(federal_calculators["trump_account"], TrumpAccount)


class TestTrumpAccountPilotWindow(TestCase):
    """Tests for pilot window boundary conditions using birth_year_month."""

    def _run_member_eligible(self, birth_year_month, age=1):
        calculator = make_calculator()
        member = make_member(age=age, birth_year_month=birth_year_month)
        e = MemberEligibility(member)
        calculator.member_eligible(e)
        return e.eligible

    def test_start_boundary_jan_2025_is_eligible(self):
        self.assertTrue(self._run_member_eligible(date(2025, 1, 1)))

    def test_end_boundary_dec_2028_is_eligible(self):
        self.assertTrue(self._run_member_eligible(date(2028, 12, 1)))

    def test_mid_window_2026_is_eligible(self):
        self.assertTrue(self._run_member_eligible(date(2026, 6, 1)))

    def test_one_month_before_window_dec_2024_is_ineligible(self):
        self.assertFalse(self._run_member_eligible(date(2024, 12, 1)))

    def test_one_month_after_window_jan_2029_is_ineligible(self):
        self.assertFalse(self._run_member_eligible(date(2029, 1, 1)))

    def test_birth_year_month_none_is_ineligible(self):
        self.assertFalse(self._run_member_eligible(None))


class TestTrumpAccountAgeCeiling(TestCase):
    """Tests for the age <= 17 (under 18) requirement."""

    def _run_member_eligible(self, age):
        calculator = make_calculator()
        member = make_member(age=age, birth_year_month=date(2025, 6, 1))
        e = MemberEligibility(member)
        calculator.member_eligible(e)
        return e.eligible

    def test_age_0_is_eligible(self):
        self.assertTrue(self._run_member_eligible(0))

    def test_age_17_is_eligible(self):
        self.assertTrue(self._run_member_eligible(17))

    def test_age_18_is_ineligible(self):
        self.assertFalse(self._run_member_eligible(18))

    def test_age_19_is_ineligible(self):
        self.assertFalse(self._run_member_eligible(19))


class TestTrumpAccountPregnancy(TestCase):
    """Tests for the pregnancy path: due date = reference_date + 280 days."""

    def _run_member_eligible(self, reference_date):
        calculator = make_calculator(reference_date=reference_date)
        member = make_member(pregnant=True)
        e = MemberEligibility(member)
        calculator.member_eligible(e)
        return e.eligible

    def test_due_date_inside_pilot_window_is_eligible(self):
        # reference_date + 280 days lands in mid-2026 (well inside window)
        reference_date = date(2025, 6, 1)
        due_date = reference_date + timedelta(days=280)
        self.assertGreaterEqual(due_date, date(2025, 1, 1))
        self.assertLessEqual(due_date, date(2028, 12, 31))
        self.assertTrue(self._run_member_eligible(reference_date))

    def test_due_date_at_pilot_start_is_eligible(self):
        # reference_date such that due_date == pilot_start exactly
        reference_date = date(2025, 1, 1) - timedelta(days=280)
        self.assertTrue(self._run_member_eligible(reference_date))

    def test_due_date_at_pilot_end_is_eligible(self):
        # reference_date such that due_date == pilot_end exactly
        reference_date = date(2028, 12, 31) - timedelta(days=280)
        self.assertTrue(self._run_member_eligible(reference_date))

    def test_due_date_before_pilot_window_is_ineligible(self):
        # reference_date such that due_date falls before Jan 2025
        reference_date = date(2024, 1, 1) - timedelta(days=280)
        self.assertFalse(self._run_member_eligible(reference_date))

    def test_due_date_after_pilot_window_is_ineligible(self):
        # reference_date such that due_date falls after Dec 2028
        reference_date = date(2029, 1, 1)
        self.assertFalse(self._run_member_eligible(reference_date))

    def test_pregnant_member_skips_birth_year_month_check(self):
        # birth_year_month=None would fail the non-pregnant path; pregnancy path ignores it
        calculator = make_calculator(reference_date=date(2025, 6, 1))
        member = make_member(pregnant=True, birth_year_month=None)
        e = MemberEligibility(member)
        calculator.member_eligible(e)
        self.assertTrue(e.eligible)


class TestTrumpAccountValue(TestCase):
    """Tests for the $1,000 value assignment."""

    def _run_full_eligible(self, birth_year_month=date(2025, 6, 1), age=1):
        calculator = make_calculator()
        member = make_member(age=age, birth_year_month=birth_year_month)
        member_e = MemberEligibility(member)
        calculator.member_eligible(member_e)

        household_e = Eligibility()
        household_e.add_member_eligibility(member_e)
        calculator.value(household_e)
        return household_e, member_e

    def test_eligible_member_receives_1000(self):
        _, member_e = self._run_full_eligible()
        self.assertTrue(member_e.eligible)
        self.assertEqual(member_e.value, 1_000)

    def test_ineligible_member_receives_0(self):
        calculator = make_calculator()
        member = make_member(age=1, birth_year_month=date(2024, 1, 1))  # outside pilot window
        member_e = MemberEligibility(member)
        calculator.member_eligible(member_e)

        household_e = Eligibility()
        household_e.add_member_eligibility(member_e)
        calculator.value(household_e)

        self.assertFalse(member_e.eligible)
        self.assertEqual(member_e.value, 0)

    def test_two_eligible_members_each_receive_1000(self):
        calculator = make_calculator()
        members = [
            make_member(age=1, birth_year_month=date(2025, 3, 1)),
            make_member(age=2, birth_year_month=date(2026, 7, 1)),
        ]
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
            self.assertEqual(me.value, 1_000)

    def test_mixed_household_only_eligible_members_receive_value(self):
        calculator = make_calculator()
        eligible_member = make_member(age=1, birth_year_month=date(2025, 6, 1))
        ineligible_member = make_member(age=1, birth_year_month=date(2024, 6, 1))

        eligible_e = MemberEligibility(eligible_member)
        ineligible_e = MemberEligibility(ineligible_member)
        calculator.member_eligible(eligible_e)
        calculator.member_eligible(ineligible_e)

        household_e = Eligibility()
        household_e.add_member_eligibility(eligible_e)
        household_e.add_member_eligibility(ineligible_e)
        calculator.value(household_e)

        self.assertEqual(eligible_e.value, 1_000)
        self.assertEqual(ineligible_e.value, 0)
