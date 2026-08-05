"""
Unit tests for the DenverPreschoolProgram (dpp) calculator.

Eligibility requirements:
  1. Household is in Denver County
  2. Member is age 3 or 4

Notes:
  - County comes from `counties_from_screen`, which prefers `screen.county` and falls back
    to a zipcode lookup, so both paths are covered here.
  - There is no income test: this is an age-and-location program only.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
from programs.programs.co import co_calculators
from programs.programs.co.denver_preschool_program.calculator import DenverPreschoolProgram
from programs.util import Dependencies, DependencyError


def make_member(age=3):
    member = Mock()
    member.age = age
    return member


def make_calculator(county="Denver County", zipcode="80205", members=None, missing_dependencies=None):
    mock_screen = Mock()
    mock_screen.county = county
    mock_screen.zipcode = zipcode
    mock_screen.household_members.all.return_value = [make_member()] if members is None else members

    return DenverPreschoolProgram(
        mock_screen,
        Mock(),
        {},
        Dependencies() if missing_dependencies is None else missing_dependencies,
    )


class TestDenverPreschoolProgramClassAttributes(TestCase):
    def test_is_subclass_of_program_calculator(self):
        self.assertTrue(issubclass(DenverPreschoolProgram, ProgramCalculator))

    def test_is_registered_in_co_calculators(self):
        self.assertIn("dpp", co_calculators)
        self.assertEqual(co_calculators["dpp"], DenverPreschoolProgram)

    def test_member_amount_is_594_a_month(self):
        self.assertEqual(DenverPreschoolProgram.member_amount, 594 * 12)

    def test_no_household_amount(self):
        self.assertEqual(DenverPreschoolProgram.amount, 0)

    def test_min_age(self):
        self.assertEqual(DenverPreschoolProgram.min_age, 3)

    def test_max_age(self):
        self.assertEqual(DenverPreschoolProgram.max_age, 4)

    def test_county(self):
        self.assertEqual(DenverPreschoolProgram.county, "Denver County")

    def test_dependencies(self):
        self.assertEqual(DenverPreschoolProgram.dependencies, ["age", "zipcode"])


class TestDenverPreschoolProgramLocation(TestCase):
    """Denver County only, resolved from `screen.county` or from the zipcode."""

    def _run(self, county, zipcode="80205"):
        calc = make_calculator(county=county, zipcode=zipcode)
        e = Eligibility()
        calc.household_eligible(e)
        return e

    def test_denver_county_is_eligible(self):
        self.assertTrue(self._run("Denver County").eligible)

    def test_jefferson_county_is_ineligible(self):
        self.assertFalse(self._run("Jefferson County").eligible)

    def test_adams_county_is_ineligible(self):
        self.assertFalse(self._run("Adams County").eligible)

    def test_denver_zipcode_is_eligible_when_county_is_unset(self):
        self.assertTrue(self._run(None, zipcode="80205").eligible)

    def test_non_denver_zipcode_is_ineligible_when_county_is_unset(self):
        self.assertFalse(self._run(None, zipcode="80401").eligible)

    def test_eligible_location_gets_a_pass_message(self):
        e = self._run("Denver County")
        self.assertEqual(len(e.pass_messages), 1)
        self.assertEqual(len(e.fail_messages), 0)

    def test_ineligible_location_gets_a_fail_message(self):
        e = self._run("Jefferson County")
        self.assertEqual(len(e.fail_messages), 1)
        self.assertEqual(len(e.pass_messages), 0)


class TestDenverPreschoolProgramMemberEligibility(TestCase):
    """Ages 3 and 4 only."""

    def _run(self, age):
        calc = make_calculator()
        e = MemberEligibility(make_member(age=age))
        calc.member_eligible(e)
        return e.eligible

    def test_age_2_is_ineligible(self):
        self.assertFalse(self._run(2))

    def test_age_3_is_eligible(self):
        self.assertTrue(self._run(3))

    def test_age_4_is_eligible(self):
        self.assertTrue(self._run(4))

    def test_age_5_is_ineligible(self):
        self.assertFalse(self._run(5))

    def test_age_0_is_ineligible(self):
        self.assertFalse(self._run(0))

    def test_adult_is_ineligible(self):
        self.assertFalse(self._run(35))


class TestDenverPreschoolProgramEligible(TestCase):
    def test_denver_household_with_a_preschooler_is_eligible(self):
        calc = make_calculator(members=[make_member(age=35), make_member(age=3)])
        self.assertTrue(calc.eligible().eligible)

    def test_denver_household_without_a_preschooler_is_ineligible(self):
        calc = make_calculator(members=[make_member(age=35), make_member(age=6)])
        self.assertFalse(calc.eligible().eligible)

    def test_non_denver_household_with_a_preschooler_is_ineligible(self):
        calc = make_calculator(county="Jefferson County", members=[make_member(age=3)])
        self.assertFalse(calc.eligible().eligible)

    def test_household_with_no_members_is_ineligible(self):
        calc = make_calculator(members=[])
        self.assertFalse(calc.eligible().eligible)


class TestDenverPreschoolProgramValue(TestCase):
    def test_one_preschooler_is_worth_one_member_amount(self):
        calc = make_calculator(members=[make_member(age=35), make_member(age=4)])
        self.assertEqual(calc.calc().value, DenverPreschoolProgram.member_amount)

    def test_two_preschoolers_are_worth_two_member_amounts(self):
        calc = make_calculator(members=[make_member(age=3), make_member(age=4)])
        self.assertEqual(calc.calc().value, 2 * DenverPreschoolProgram.member_amount)

    def test_ineligible_members_add_no_value(self):
        calc = make_calculator(members=[make_member(age=3), make_member(age=10)])
        self.assertEqual(calc.calc().value, DenverPreschoolProgram.member_amount)

    def test_ineligible_household_is_worth_nothing(self):
        calc = make_calculator(county="Jefferson County", members=[make_member(age=3)])
        self.assertEqual(calc.calc().value, 0)


class TestDenverPreschoolProgramCanCalc(TestCase):
    def test_can_calc_with_no_missing_dependencies(self):
        self.assertTrue(make_calculator().can_calc())

    def test_cannot_calc_without_age(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["age"])).can_calc())

    def test_cannot_calc_without_zipcode(self):
        self.assertFalse(make_calculator(missing_dependencies=Dependencies(["zipcode"])).can_calc())

    def test_can_calc_with_an_unrelated_missing_dependency(self):
        self.assertTrue(make_calculator(missing_dependencies=Dependencies(["insurance"])).can_calc())

    def test_calc_raises_when_a_dependency_is_missing(self):
        calc = make_calculator(missing_dependencies=Dependencies(["age"]))
        with self.assertRaises(DependencyError):
            calc.calc()
