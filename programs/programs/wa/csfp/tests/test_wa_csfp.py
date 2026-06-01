from django.test import TestCase
from unittest.mock import Mock

from programs.programs.wa import wa_calculators
from programs.programs.wa.csfp.calculator import WaCsfp
from programs.programs.calc import Eligibility, MemberEligibility


def make_member(age=65):
    member = Mock()
    member.age = age
    return member


def make_calculator(yearly_income=10_000, fpl_limit=15_000, members=None):
    mock_screen = Mock()
    mock_screen.calc_gross_income = Mock(return_value=yearly_income)
    mock_screen.household_members.all = Mock(return_value=members or [make_member()])
    mock_screen.has_benefit = Mock(return_value=False)

    mock_program = Mock()
    mock_program.year.get_limit = Mock(return_value=fpl_limit)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return WaCsfp(mock_screen, mock_program, {}, mock_missing_deps)


class TestWaCsfpClassAttributes(TestCase):
    def test_is_registered(self):
        self.assertIn("wa_csfp", wa_calculators)
        self.assertEqual(wa_calculators["wa_csfp"], WaCsfp)

    def test_min_age(self):
        self.assertEqual(WaCsfp.min_age, 60)

    def test_fpl_percent(self):
        self.assertEqual(WaCsfp.fpl_percent, 1.5)

    def test_member_amount(self):
        self.assertEqual(WaCsfp.member_amount, 50 * 12)


class TestWaCsfpMemberEligibility(TestCase):
    def _run(self, age):
        calc = make_calculator()
        e = MemberEligibility(make_member(age=age))
        calc.member_eligible(e)
        return e.eligible

    def test_age_60_eligible(self):
        self.assertTrue(self._run(60))

    def test_age_68_eligible(self):
        self.assertTrue(self._run(68))

    def test_age_59_ineligible(self):
        self.assertFalse(self._run(59))

    def test_age_none_ineligible(self):
        self.assertFalse(self._run(None))


class TestWaCsfpHouseholdEligibility(TestCase):
    # FPL limit = 15_000; income threshold = 1.5 * 15_000 = 22_500

    def _run(self, yearly_income, fpl_limit=15_000, already_has_csfp=False):
        calc = make_calculator(yearly_income=yearly_income, fpl_limit=fpl_limit)
        calc.screen.has_benefit = Mock(return_value=already_has_csfp)
        e = Eligibility()
        me = MemberEligibility(make_member())
        me.eligible = True
        e.add_member_eligibility(me)
        calc.household_eligible(e)
        return e.eligible

    def test_income_below_limit_eligible(self):
        self.assertTrue(self._run(yearly_income=10_000))

    def test_income_at_limit_eligible(self):
        # exactly at 150% FPL: 1.5 * 15_000 = 22_500
        self.assertTrue(self._run(yearly_income=22_500))

    def test_income_above_limit_ineligible(self):
        self.assertFalse(self._run(yearly_income=22_501))

    def test_income_well_above_limit_ineligible(self):
        self.assertFalse(self._run(yearly_income=50_000))

    def test_already_receiving_csfp_ineligible(self):
        self.assertFalse(self._run(yearly_income=10_000, already_has_csfp=True))


class TestWaCsfpValue(TestCase):
    def test_single_eligible_senior_value_600(self):
        senior = make_member(age=65)
        calc = make_calculator(yearly_income=10_000, members=[senior])
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 600)

    def test_two_eligible_seniors_value_1200(self):
        senior1 = make_member(age=72)
        senior2 = make_member(age=68)
        calc = make_calculator(yearly_income=10_000, members=[senior1, senior2])
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1200)

    def test_mixed_household_one_senior_one_young_value_600(self):
        # Only the 65-year-old is eligible; 45-year-old is not
        senior = make_member(age=65)
        young = make_member(age=45)
        calc = make_calculator(yearly_income=10_000, members=[senior, young])
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 600)

    def test_no_eligible_members_value_0(self):
        # No member is 60+, so household is ineligible
        young = make_member(age=45)
        calc = make_calculator(yearly_income=10_000, members=[young])
        result = calc.calc()
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

    def test_income_too_high_value_0(self):
        senior = make_member(age=65)
        # 1.5 * 15_000 = 22_500; income = 30_000 is over limit
        calc = make_calculator(yearly_income=30_000, fpl_limit=15_000, members=[senior])
        result = calc.calc()
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)
