"""MySpark (myspark) — first tests.

Denver 11-to-14-year-olds whose household qualifies for free or reduced school meals. The
free-or-reduced-lunch condition is read from `nslp`, a PolicyEngine program, which is why
it stays a dependency: `school_meal_net_subsidy` folds in categorical eligibility through
SNAP/TANF, a K-12 enrolment PolicyEngine derives internally, and an SPM-unit foster-care
path. There is no equivalent condition on this household's own facts to restate.

Households are hand-rolled on Mock screens. `CustomCalculatorTestCase` would replace the
boilerplate; it is still unmerged.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.white_labels.co.myspark.calculator import MySpark
from programs.util import Dependencies, DependencyError, UpstreamAbsentError


def make_member(age):
    member = Mock()
    member.age = age
    return member


def make_data(nslp_eligible=None):
    if nslp_eligible is None:
        return {}

    nslp = Eligibility()
    nslp.eligible = nslp_eligible
    return {"nslp": nslp}


def make_calculator(nslp_eligible=True, county="Denver County", ages=(12,), missing_dependencies=None):
    screen = Mock()
    screen.county = county
    screen.household_members.all.return_value = [make_member(age) for age in ages]

    return MySpark(
        screen,
        Mock(),
        make_data(nslp_eligible),
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class TestRegistration(TestCase):
    def test_is_a_program_calculator(self):
        self.assertTrue(issubclass(MySpark, ProgramCalculator))

    def test_program_code(self):
        """Not `co_my_spark`, which is what the coupling-removal ticket originally called
        it."""
        self.assertEqual(MySpark.program_code, "myspark")

    def test_declares_its_nslp_gate(self):
        self.assertEqual(MySpark.gates_on, ("nslp",))


class TestFreeOrReducedLunchIsNecessaryNotSufficient(TestCase):
    def _eligible(self, **kwargs):
        e = Eligibility()
        make_calculator(**kwargs).household_eligible(e)
        return e.eligible

    def test_lunch_eligible_denver_household_is_eligible(self):
        self.assertTrue(self._eligible())

    def test_lunch_eligible_household_outside_denver_is_not(self):
        self.assertFalse(self._eligible(county="Boulder County"))

    def test_denver_household_not_eligible_for_lunch_is_not(self):
        self.assertFalse(self._eligible(nslp_eligible=False))


class TestTheNslpGateDoesNotGuess(TestCase):
    def test_uncalculated_nslp_raises(self):
        """`nslp` is PolicyEngine-backed, so an outage or a payload failure leaves no
        result at all. Raising drops MySpark from the results rather than telling the
        household they do not qualify."""
        with self.assertRaises(DependencyError):
            make_calculator(nslp_eligible=None).household_eligible(Eligibility())

    def test_the_raise_names_the_upstream(self):
        with self.assertRaises(UpstreamAbsentError) as caught:
            make_calculator(nslp_eligible=None).household_eligible(Eligibility())

        self.assertEqual(caught.exception.program_code, "nslp")


class TestAgeBand(TestCase):
    def _member_eligible(self, age):
        e = MemberEligibility(make_member(age))
        make_calculator().member_eligible(e)
        return e.eligible

    def test_below_the_band_is_not_eligible(self):
        self.assertFalse(self._member_eligible(10))

    def test_the_lower_bound_is_eligible(self):
        self.assertTrue(self._member_eligible(11))

    def test_the_upper_bound_is_eligible(self):
        self.assertTrue(self._member_eligible(14))

    def test_above_the_band_is_not_eligible(self):
        self.assertFalse(self._member_eligible(15))


class TestValue(TestCase):
    def test_it_pays_per_eligible_member(self):
        calculator = make_calculator(ages=(12, 13))
        self.assertEqual(calculator.calc().value, 2 * MySpark.member_amount)

    def test_an_out_of_band_sibling_is_not_paid_for(self):
        calculator = make_calculator(ages=(12, 30))
        self.assertEqual(calculator.calc().value, MySpark.member_amount)

    def test_a_household_with_no_in_band_member_is_worth_nothing(self):
        self.assertEqual(make_calculator(ages=(30,)).calc().value, 0)


class TestCanCalc(TestCase):
    def test_can_calc_with_nothing_missing(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_its_own_fields(self):
        for field in ("age", "zipcode"):
            with self.subTest(field=field):
                self.assertFalse(make_calculator(missing_dependencies=Dependencies([field])).can_calc())

    def test_cannot_calc_without_the_income_fields_nslp_reads(self):
        """`nslp` sends `school_meal_countable_income`, so it needs the income fields even
        though MySpark's own conditions do not. Without this, MySpark would be calculable
        on a screen where `nslp` is not and the gate would raise."""
        self.assertNotIn("income_amount", MySpark.dependencies)
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["income_amount"])).can_calc())

    def test_can_calc_with_a_field_neither_program_reads(self):
        self.assertTrue(make_calculator(missing_dependencies=Dependencies(["expense_amount"])).can_calc())
