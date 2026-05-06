from django.test import TestCase
from unittest.mock import Mock, patch
from datetime import date

from programs.programs.federal.pe import member
from programs.programs.wa import wa_calculators
from programs.programs.wa.ssdi.calculator import WaSsdi
from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility


def make_member(
    age=40,
    birth_year=1985,
    birth_month=6,
    long_term_disability=True,
    visually_impaired=False,
    earned_monthly=500,
    ssdi_yearly=0,
    ss_retirement_yearly=0,
):
    member = Mock()
    member.age = age
    member.birth_year = birth_year
    member.birth_month = birth_month
    member.long_term_disability = long_term_disability
    member.visually_impaired = visually_impaired

    def calc_gross_income(freq, types, **kwargs):
        if types == ["earned"]:
            if freq == "monthly":
                return earned_monthly
            return earned_monthly * 12
        if types == ["sSDisability"]:
            return ssdi_yearly if freq == "yearly" else ssdi_yearly / 12
        if types == ["sSRetirement"]:
            return ss_retirement_yearly if freq == "yearly" else ss_retirement_yearly / 12
        return 0

    member.calc_gross_income = Mock(side_effect=calc_gross_income)
    return member


def make_calculator(has_ssdi=False):
    mock_screen = Mock()
    mock_screen.has_benefit = Mock(side_effect=lambda b: has_ssdi if b == "ssdi" else False)
    mock_screen.household_members.all.return_value = []
    mock_screen.get_reference_date.return_value = date(2026, 4, 30)

    mock_program = Mock()
    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return WaSsdi(mock_screen, mock_program, {}, mock_missing_deps)


class TestWaSsdiClassAttributes(TestCase):
    def test_is_registered(self):
        self.assertIn("wa_ssdi", wa_calculators)
        self.assertEqual(wa_calculators["wa_ssdi"], WaSsdi)

    def test_sga_thresholds(self):
        self.assertEqual(WaSsdi.sga_non_blind, 1_690)
        self.assertEqual(WaSsdi.sga_blind, 2_830)

    def test_member_amount(self):
        self.assertEqual(WaSsdi.member_amount, 1_634)


class TestWaSsdiFraSchedule(TestCase):
    def test_born_1954_fra_is_66_0(self):
        self.assertEqual(WaSsdi._get_fra(1954), (66, 0))

    def test_born_1955_fra_is_66_2(self):
        self.assertEqual(WaSsdi._get_fra(1955), (66, 2))

    def test_born_1957_fra_is_66_6(self):
        self.assertEqual(WaSsdi._get_fra(1957), (66, 6))

    def test_born_1960_fra_is_67_0(self):
        self.assertEqual(WaSsdi._get_fra(1960), (67, 0))

    def test_born_1943_fra_is_66_0(self):
        self.assertEqual(WaSsdi._get_fra(1943), (66, 0))

    def test_born_1970_fra_is_67_0(self):
        self.assertEqual(WaSsdi._get_fra(1970), (67, 0))


class TestWaSsdiMemberEligibility(TestCase):
    def _run(self, member):
        calc = make_calculator()
        e = MemberEligibility(member)
        calc.member_eligible(e)
        return e.eligible

    def test_standard_eligible(self):
        self.assertTrue(self._run(make_member(age=44, birth_year=1981, long_term_disability=True, earned_monthly=500)))

    def test_no_disability_ineligible(self):
        self.assertFalse(self._run(make_member(long_term_disability=False)))

    def test_income_above_sga_ineligible(self):
        self.assertFalse(self._run(make_member(earned_monthly=1700)))

    def test_income_exactly_at_sga_eligible(self):
        self.assertTrue(self._run(make_member(earned_monthly=1690)))

    def test_blind_higher_sga_eligible(self):
        self.assertTrue(self._run(make_member(visually_impaired=True, earned_monthly=2500)))

    def test_blind_above_blind_sga_ineligible(self):
        self.assertFalse(self._run(make_member(visually_impaired=True, earned_monthly=2831)))

    def test_already_receiving_ssdi_ineligible(self):
        self.assertFalse(self._run(make_member(ssdi_yearly=14400)))

    def test_already_receiving_ss_retirement_ineligible(self):
        self.assertFalse(self._run(make_member(ss_retirement_yearly=18000)))

    @patch("programs.programs.wa.ssdi.calculator.date")
    def test_over_fra_ineligible(self, mock_date):
        member = make_member(age=68, birth_year=1957, birth_month=1)
        self.assertFalse(self._run(member))

    @patch("programs.programs.wa.ssdi.calculator.date")
    def test_under_fra_born_1960_eligible(self, mock_date):
        member = make_member(age=65, birth_year=1960, birth_month=11)
        self.assertTrue(self._run(member))

class TestWaSsdiHouseholdEligibility(TestCase):
    def _run(self, has_ssdi=False, eligible_members=None):
        calc = make_calculator(has_ssdi=has_ssdi)
        e = Eligibility()
        for member in (eligible_members or [make_member()]):
            me = MemberEligibility(member)
            me.eligible = True
            e.add_member_eligibility(me)
        calc.household_eligible(e)
        return e.eligible

    def test_eligible_household(self):
        self.assertTrue(self._run())

    def test_already_has_ssdi_ineligible(self):
        self.assertFalse(self._run(has_ssdi=True))

    def test_no_eligible_members_ineligible(self):
        calc = make_calculator()
        e = Eligibility()
        me = MemberEligibility(make_member(long_term_disability=False))
        me.eligible = False
        e.add_member_eligibility(me)
        calc.household_eligible(e)
        self.assertFalse(e.eligible)


class TestWaSsdiValue(TestCase):
    @patch("programs.programs.wa.ssdi.calculator.date")
    def test_eligible_member_gets_1634(self, mock_date):
        mock_date.today.return_value = date(2026, 4, 30)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        calc = make_calculator()
        member = make_member()
        calc.screen.household_members.all.return_value = [member]
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1634)

    @patch("programs.programs.wa.ssdi.calculator.date")
    def test_multi_member_one_eligible(self, mock_date):
        mock_date.today.return_value = date(2026, 4, 30)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        calc = make_calculator()
        eligible = make_member(age=44, birth_year=1981, long_term_disability=True, earned_monthly=500)
        ineligible = make_member(age=24, birth_year=2001, long_term_disability=False, earned_monthly=2500)
        calc.screen.household_members.all.return_value = [eligible, ineligible]
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 1634)
