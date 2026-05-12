"""
Unit tests for WaHeadStart calculator.

Eligibility requirements:
  1. Member age: under 3 OR pregnant (EHS path), OR ages 3–5 (HS Preschool path)
  2. Household financial pathway (any one of):
     - Income <= 100% FPL
     - Receives TANF, SSI, or SNAP (household-level categorical)
     - An age-eligible child is in foster care
  3. Exclusion: household already receives Head Start
"""

from django.test import TestCase
from unittest.mock import Mock, MagicMock

from programs.programs.wa import wa_calculators
from programs.programs.wa.head_start.calculator import WaHeadStart
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility


def make_calculator(
    has_head_start=False,
    has_snap=False,
    has_tanf=False,
    has_ssi=False,
    household_income=0,
    household_size=3,
    fpl_limit=27320,
):
    mock_program = Mock()
    mock_program.year.get_limit.return_value = fpl_limit

    mock_screen = Mock()
    mock_screen.household_size = household_size
    mock_screen.has_benefit = Mock(
        side_effect=lambda b: {
            "wa_head_start": has_head_start,
            "snap": has_snap,
            "tanf": has_tanf,
            "ssi": has_ssi,
        }.get(b, False)
    )
    mock_screen.calc_gross_income = Mock(return_value=household_income)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return WaHeadStart(mock_screen, mock_program, {}, mock_missing_deps)


def make_member(age=30, pregnant=False, relationship="child"):
    member = Mock()
    member.age = age
    member.pregnant = pregnant
    member.relationship = relationship
    return member


def make_eligible_member_e(member):
    me = MemberEligibility(member)
    me.eligible = True
    return me


class TestWaHeadStartClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(WaHeadStart, ProgramCalculator))

    def test_is_registered_in_wa_calculators(self):
        self.assertIn("wa_head_start", wa_calculators)
        self.assertEqual(wa_calculators["wa_head_start"], WaHeadStart)

    def test_hs_min_age(self):
        self.assertEqual(WaHeadStart.hs_min_age, 3)

    def test_hs_max_age(self):
        self.assertEqual(WaHeadStart.hs_max_age, 5)

    def test_ehs_max_age(self):
        self.assertEqual(WaHeadStart.ehs_max_age, 3)

    def test_fpl_percent_is_1(self):
        self.assertEqual(WaHeadStart.fpl_percent, 1.0)

    def test_member_amount_is_10381(self):
        self.assertEqual(WaHeadStart.member_amount, 10_381)


class TestWaHeadStartMemberEligibility(TestCase):
    """Age and pregnancy gate in member_eligible."""

    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    # EHS path
    def test_age_0_is_eligible_ehs(self):
        self.assertTrue(self._run(make_member(age=0)))

    def test_age_1_is_eligible_ehs(self):
        self.assertTrue(self._run(make_member(age=1)))

    def test_age_2_is_eligible_ehs(self):
        self.assertTrue(self._run(make_member(age=2)))

    def test_pregnant_adult_is_eligible_ehs(self):
        self.assertTrue(self._run(make_member(age=30, pregnant=True, relationship="headOfHousehold")))

    # HS Preschool path
    def test_age_3_is_eligible_hs(self):
        self.assertTrue(self._run(make_member(age=3)))

    def test_age_4_is_eligible_hs(self):
        self.assertTrue(self._run(make_member(age=4)))

    def test_age_5_is_eligible_hs(self):
        self.assertTrue(self._run(make_member(age=5)))

    # Ineligible
    def test_age_6_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=6)))

    def test_age_7_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=7)))

    def test_age_30_not_pregnant_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=30, pregnant=False)))

    def test_age_none_is_ineligible(self):
        self.assertFalse(self._run(make_member(age=None)))


class TestWaHeadStartHouseholdExclusion(TestCase):
    """Already-enrolled exclusion."""

    def _run(self, has_head_start, household_income, fpl_limit):
        calc = make_calculator(has_head_start=has_head_start, household_income=household_income, fpl_limit=fpl_limit)
        child = make_member(age=4)
        e = Eligibility()
        e.add_member_eligibility(make_eligible_member_e(child))
        calc.household_eligible(e)
        return e.eligible

    def test_already_has_head_start_is_ineligible(self):
        self.assertFalse(self._run(has_head_start=True, household_income=10000, fpl_limit=27320))

    def test_not_enrolled_is_eligible_when_income_qualifies(self):
        self.assertTrue(self._run(has_head_start=False, household_income=10000, fpl_limit=27320))


class TestWaHeadStartIncomeEligibility(TestCase):
    """Income test: 100% FPL threshold."""

    def _run(self, household_income, fpl_limit=27320):
        calc = make_calculator(household_income=household_income, fpl_limit=fpl_limit)
        child = make_member(age=4)
        e = Eligibility()
        e.add_member_eligibility(make_eligible_member_e(child))
        calc.household_eligible(e)
        return e.eligible

    def test_income_below_fpl_is_eligible(self):
        self.assertTrue(self._run(household_income=14400))

    def test_income_exactly_at_fpl_is_eligible(self):
        self.assertTrue(self._run(household_income=27320))

    def test_income_one_dollar_above_fpl_is_ineligible(self):
        # No categorical pathway configured — only income gate
        self.assertFalse(self._run(household_income=27321))


class TestWaHeadStartCategoricalEligibility(TestCase):
    """TANF, SSI, SNAP, and foster care bypass the income test."""

    def _run_with_benefit(self, has_tanf=False, has_ssi=False, has_snap=False, household_income=99999):
        calc = make_calculator(
            has_tanf=has_tanf,
            has_ssi=has_ssi,
            has_snap=has_snap,
            household_income=household_income,
            fpl_limit=27320,
        )
        child = make_member(age=4)
        e = Eligibility()
        e.add_member_eligibility(make_eligible_member_e(child))
        calc.household_eligible(e)
        return e.eligible

    def test_tanf_bypasses_income_test(self):
        self.assertTrue(self._run_with_benefit(has_tanf=True))

    def test_ssi_bypasses_income_test(self):
        self.assertTrue(self._run_with_benefit(has_ssi=True))

    def test_snap_bypasses_income_test(self):
        self.assertTrue(self._run_with_benefit(has_snap=True))

    def test_no_categorical_and_high_income_is_ineligible(self):
        self.assertFalse(self._run_with_benefit())

    def test_foster_child_bypasses_income_test(self):
        calc = make_calculator(household_income=99999, fpl_limit=27320)
        foster = make_member(age=4, relationship="fosterChild")
        e = Eligibility()
        e.add_member_eligibility(make_eligible_member_e(foster))
        calc.household_eligible(e)
        self.assertTrue(e.eligible)

    def test_non_foster_child_does_not_trigger_foster_bypass(self):
        calc = make_calculator(household_income=99999, fpl_limit=27320)
        child = make_member(age=4, relationship="child")
        e = Eligibility()
        e.add_member_eligibility(make_eligible_member_e(child))
        calc.household_eligible(e)
        self.assertFalse(e.eligible)


class TestWaHeadStartBenefitValue(TestCase):
    """member_amount = $10,381 per eligible participant."""

    def test_single_eligible_member_value(self):
        calc = make_calculator(household_income=10000, fpl_limit=27320)
        member = make_member(age=4)
        e = MemberEligibility(member)
        e.eligible = True
        self.assertEqual(calc.member_value(member), 10_381)

    def test_two_eligible_members_double_value(self):
        """Full calc() path: ages 4 + 2 → 2 × $10,381 = $20,762."""
        mock_program = Mock()
        mock_program.year.get_limit.return_value = 27320

        mock_screen = Mock()
        mock_screen.household_size = 3
        mock_screen.has_benefit = Mock(return_value=False)
        mock_screen.calc_gross_income = Mock(return_value=14400)
        mock_screen.household_members.all = Mock(
            return_value=[
                make_member(age=32, relationship="headOfHousehold"),
                make_member(age=4),
                make_member(age=2),
            ]
        )

        mock_missing_deps = Mock()
        mock_missing_deps.has.return_value = False

        calc = WaHeadStart(mock_screen, mock_program, {}, mock_missing_deps)
        result = calc.calc()

        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 20_762)

    def test_pregnant_woman_alone_value(self):
        """Pregnant woman (no children) → 1 × $10,381."""
        mock_program = Mock()
        mock_program.year.get_limit.return_value = 15960

        mock_screen = Mock()
        mock_screen.household_size = 1
        mock_screen.has_benefit = Mock(return_value=False)
        mock_screen.calc_gross_income = Mock(return_value=14400)
        mock_screen.household_members.all = Mock(
            return_value=[make_member(age=27, pregnant=True, relationship="headOfHousehold")]
        )

        mock_missing_deps = Mock()
        mock_missing_deps.has.return_value = False

        calc = WaHeadStart(mock_screen, mock_program, {}, mock_missing_deps)
        result = calc.calc()

        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 10_381)
