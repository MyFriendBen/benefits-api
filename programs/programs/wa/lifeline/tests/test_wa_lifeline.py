from django.test import TestCase
from unittest.mock import Mock

from programs.programs.wa import wa_calculators
from programs.programs.wa.lifeline.calculator import WaLifeline
from programs.programs.calc import Eligibility, MemberEligibility


def make_member(has_medicaid=False):
    member = Mock()
    member.has_benefit = Mock(side_effect=lambda name: has_medicaid if name == "medicaid" else False)
    return member


def make_calculator(
    yearly_income=10_000,
    fpl_limit=15_960,
    has_lifeline=False,
    has_snap=False,
    has_ssi=False,
    has_tanf=False,
    has_section_8=False,
    has_wic=False,
    has_medicaid=False,
    members=None,
):
    mock_screen = Mock()
    mock_screen.calc_gross_income = Mock(return_value=yearly_income)

    benefit_map = {
        "lifeline": has_lifeline,
        "snap": has_snap,
        "ssi": has_ssi,
        "tanf": has_tanf,
        "section_8": has_section_8,
        "wic": has_wic,
        "medicaid": has_medicaid,
    }
    mock_screen.has_benefit = Mock(side_effect=lambda name: benefit_map.get(name, False))
    mock_screen.household_members.all = Mock(return_value=members or [make_member()])

    mock_program = Mock()
    mock_program.year.get_limit = Mock(return_value=fpl_limit)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return WaLifeline(mock_screen, mock_program, {}, mock_missing_deps)


class TestWaLifelineClassAttributes(TestCase):
    def test_is_registered(self):
        self.assertIn("wa_lifeline", wa_calculators)
        self.assertEqual(wa_calculators["wa_lifeline"], WaLifeline)

    def test_fpl_percent(self):
        self.assertEqual(WaLifeline.fpl_percent, 1.35)

    def test_amount(self):
        # $9.25/month × 12 = $111/year
        self.assertEqual(WaLifeline.amount, 111)


class TestWaLifelineHouseholdEligibility(TestCase):
    # 2026 FPL base (1 person) = $15,960; 135% = $21,546
    # Using fpl_limit=15_960 → income_limit = ceil(1.35 * 15_960) = 21_546

    def _run(self, **kwargs):
        calc = make_calculator(**kwargs)
        e = Eligibility()
        me = MemberEligibility(make_member())
        me.eligible = True
        e.add_member_eligibility(me)
        calc.household_eligible(e)
        return e.eligible

    def test_income_below_fpl_limit_eligible(self):
        self.assertTrue(self._run(yearly_income=15_000))

    def test_income_at_fpl_limit_eligible(self):
        # ceil(1.35 * 15_960) = 21_546
        self.assertTrue(self._run(yearly_income=21_546))

    def test_income_above_fpl_limit_no_programs_ineligible(self):
        self.assertFalse(self._run(yearly_income=30_000))

    def test_already_has_lifeline_ineligible(self):
        self.assertFalse(self._run(yearly_income=10_000, has_lifeline=True))

    def test_already_has_lifeline_overrides_snap(self):
        self.assertFalse(self._run(yearly_income=10_000, has_lifeline=True, has_snap=True))

    def test_snap_categorical_eligible_over_income(self):
        self.assertTrue(self._run(yearly_income=50_000, has_snap=True))

    def test_ssi_categorical_eligible_over_income(self):
        self.assertTrue(self._run(yearly_income=50_000, has_ssi=True))

    def test_tanf_categorical_eligible_over_income(self):
        self.assertTrue(self._run(yearly_income=50_000, has_tanf=True))

    def test_section_8_categorical_eligible_over_income(self):
        self.assertTrue(self._run(yearly_income=50_000, has_section_8=True))

    def test_wic_categorical_eligible_over_income(self):
        self.assertTrue(self._run(yearly_income=50_000, has_wic=True))

    def test_screen_level_medicaid_eligible_over_income(self):
        self.assertTrue(self._run(yearly_income=50_000, has_medicaid=True))

    def test_member_level_medicaid_eligible_over_income(self):
        member_with_medicaid = make_member(has_medicaid=True)
        self.assertTrue(self._run(yearly_income=50_000, members=[member_with_medicaid]))

    def test_no_programs_income_just_above_limit_ineligible(self):
        # income = 30,000 > 135% FPL for household of 2 (29,214)
        self.assertFalse(self._run(yearly_income=30_000, fpl_limit=21_640))


class TestWaLifelineValue(TestCase):
    def test_eligible_household_value_111(self):
        calc = make_calculator(yearly_income=10_000, has_snap=True)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 111)

    def test_ineligible_household_value_0(self):
        calc = make_calculator(yearly_income=50_000)
        result = calc.calc()
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

    def test_income_based_eligible_value_111(self):
        calc = make_calculator(yearly_income=15_000)
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 111)
