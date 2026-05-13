from django.test import TestCase
from unittest.mock import Mock

from programs.programs.wa import wa_calculators
from programs.programs.wa.wic.calculator import WaWic
from programs.programs.calc import Eligibility, MemberEligibility


def make_member(age=30, pregnant=False, relationship="headOfHousehold"):
    member = Mock()
    member.age = age
    member.pregnant = pregnant
    member.relationship = relationship
    return member


def make_calculator(yearly_income=10_000, fpl_limit=15_000, members=None, has_benefit=None):
    if has_benefit is None:
        has_benefit = {}
    mock_screen = Mock()
    mock_screen.calc_gross_income = Mock(return_value=yearly_income)
    mock_screen.household_members.all = Mock(return_value=members or [make_member()])
    mock_screen.household_size = len(members) if members else 1
    mock_screen.has_benefit = Mock(side_effect=lambda b: has_benefit.get(b, False))

    mock_program = Mock()
    mock_program.year.get_limit = Mock(return_value=fpl_limit)

    mock_missing_deps = Mock()
    mock_missing_deps.has.return_value = False

    return WaWic(mock_screen, mock_program, {}, mock_missing_deps)


class TestWaWicClassAttributes(TestCase):
    def test_is_registered(self):
        self.assertIn("wa_wic", wa_calculators)
        self.assertEqual(wa_calculators["wa_wic"], WaWic)

    def test_fpl_percent(self):
        self.assertEqual(WaWic.fpl_percent, 1.85)

    def test_member_amount_is_annual(self):
        self.assertEqual(WaWic.member_amount, 80 * 12)

    def test_max_child_age(self):
        self.assertEqual(WaWic.max_child_age, 5)


class TestWaWicMemberEligibility(TestCase):
    def _run(self, age=30, pregnant=False):
        calc = make_calculator()
        e = MemberEligibility(make_member(age=age, pregnant=pregnant))
        calc.member_eligible(e)
        return e.eligible

    def test_pregnant_woman_eligible(self):
        self.assertTrue(self._run(age=29, pregnant=True))

    def test_infant_under_1_eligible(self):
        self.assertTrue(self._run(age=0))

    def test_child_age_1_eligible(self):
        self.assertTrue(self._run(age=1))

    def test_child_age_3_eligible(self):
        self.assertTrue(self._run(age=3))

    def test_child_age_4_eligible(self):
        self.assertTrue(self._run(age=4))

    def test_child_age_5_ineligible(self):
        self.assertFalse(self._run(age=5))

    def test_child_age_6_ineligible(self):
        self.assertFalse(self._run(age=6))

    def test_adult_not_pregnant_ineligible(self):
        self.assertFalse(self._run(age=35, pregnant=False))

    def test_age_none_not_pregnant_ineligible(self):
        self.assertFalse(self._run(age=None, pregnant=False))

    def test_age_none_pregnant_eligible(self):
        self.assertTrue(self._run(age=None, pregnant=True))


class TestWaWicHouseholdEligibility(TestCase):
    def _run(self, yearly_income=10_000, fpl_limit=15_000, has_benefit=None, members=None):
        if members is None:
            members = [make_member(age=29, pregnant=True)]
        calc = make_calculator(
            yearly_income=yearly_income,
            fpl_limit=fpl_limit,
            members=members,
            has_benefit=has_benefit,
        )
        e = Eligibility()
        for m in members:
            me = MemberEligibility(m)
            me.eligible = True
            e.add_member_eligibility(me)
        calc.household_eligible(e)
        return e.eligible

    def test_income_below_limit_eligible(self):
        self.assertTrue(self._run(yearly_income=10_000))

    def test_income_at_limit_eligible(self):
        # 1.85 * 15_000 = 27_750; ceil = 27_750
        self.assertTrue(self._run(yearly_income=27_750))

    def test_income_above_limit_ineligible(self):
        self.assertFalse(self._run(yearly_income=27_751))

    def test_snap_adjunctive_bypasses_income(self):
        self.assertTrue(self._run(yearly_income=50_000, has_benefit={"snap": True}))

    def test_medicaid_adjunctive_bypasses_income(self):
        self.assertTrue(self._run(yearly_income=50_000, has_benefit={"medicaid": True}))

    def test_tanf_adjunctive_bypasses_income(self):
        self.assertTrue(self._run(yearly_income=50_000, has_benefit={"tanf": True}))

    def test_no_adjunctive_income_over_ineligible(self):
        self.assertFalse(self._run(yearly_income=50_000, has_benefit={}))


class TestWaWicHouseholdSizeAdjustment(TestCase):
    def test_pregnant_member_adds_one_to_household_size(self):
        pregnant_mom = make_member(age=29, pregnant=True)
        child = make_member(age=2, relationship="child")
        calc = make_calculator(members=[pregnant_mom, child])
        self.assertEqual(calc._wic_household_size(), 3)

    def test_no_pregnant_members_unchanged(self):
        adult = make_member(age=30)
        child = make_member(age=3, relationship="child")
        calc = make_calculator(members=[adult, child])
        self.assertEqual(calc._wic_household_size(), 2)


class TestWaWicMemberValue(TestCase):
    def test_pregnant_member_gets_double_value(self):
        calc = make_calculator()
        pregnant = make_member(age=29, pregnant=True)
        self.assertEqual(calc.member_value(pregnant), 80 * 12 * 2)

    def test_child_gets_single_value(self):
        calc = make_calculator()
        child = make_member(age=3, pregnant=False)
        self.assertEqual(calc.member_value(child), 80 * 12)


class TestWaWicEndToEnd(TestCase):
    def test_pregnant_woman_with_child_eligible(self):
        mom = make_member(age=29, pregnant=True)
        child = make_member(age=2, relationship="child")
        calc = make_calculator(yearly_income=21_600, members=[mom, child])
        result = calc.calc()
        self.assertTrue(result.eligible)
        # mom (pregnant) = 1920, child = 960 → total 2880
        self.assertEqual(result.value, 2880)

    def test_adults_only_no_pregnancy_ineligible(self):
        adult1 = make_member(age=40)
        adult2 = make_member(age=38)
        calc = make_calculator(yearly_income=10_000, members=[adult1, adult2])
        result = calc.calc()
        self.assertFalse(result.eligible)
        self.assertEqual(result.value, 0)

    def test_mixed_household_only_young_child_eligible(self):
        adult = make_member(age=35)
        toddler = make_member(age=3, relationship="child")
        older_child = make_member(age=6, relationship="child")
        calc = make_calculator(yearly_income=10_000, members=[adult, toddler, older_child])
        result = calc.calc()
        self.assertTrue(result.eligible)
        # only toddler eligible = 960
        self.assertEqual(result.value, 960)

    def test_snap_adjunctive_with_child(self):
        adult = make_member(age=33)
        spouse = make_member(age=33)
        child = make_member(age=3, relationship="child")
        calc = make_calculator(
            yearly_income=54_000,
            members=[adult, spouse, child],
            has_benefit={"snap": True},
        )
        result = calc.calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 960)
