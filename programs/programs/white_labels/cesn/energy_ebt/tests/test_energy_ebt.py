"""
Energy EBT excludes households that can get LEAP, so it reads `cesn_leap` strictly.

The exclusion is a union: already receiving LEAP, or eligible for it. Both disqualify.
That polarity is why this gate raises on an uncalculated upstream instead of tolerating
it the way the CESN affordability programs do — there, absence costs a household one way
to qualify; here it would wave them past the screen-out and offer a program they should
not be offered.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.framework.base import Eligibility
from programs.programs.cross_white_label.liheap.cesn import EnergyCalculatorEnergyAssistance
from programs.programs.white_labels.cesn.energy_ebt.calculator import EnergyCalculatorEnergyEbt
from programs.util import DependencyError


def make_calculator(reports_leap=False, leap_eligible=None, income=0, household_size=2):
    """`leap_eligible=None` models cesn_leap never being calculated."""
    data = {}
    if leap_eligible is not None:
        leap = Eligibility()
        leap.eligible = leap_eligible
        data["cesn_leap"] = leap

    screen = Mock()
    screen.has_benefit.return_value = reports_leap
    screen.calc_gross_income.return_value = income
    screen.household_size = household_size
    screen.household_members.all.return_value = []

    program = Mock()
    program.year.as_dict.return_value = {household_size: 50_000}

    return EnergyCalculatorEnergyEbt(screen, program, data, Mock())


def run(**kwargs):
    e = Eligibility()
    make_calculator(**kwargs).household_eligible(e)
    return e.eligible


class TestLeapExclusion(TestCase):
    def test_household_that_cannot_get_leap_is_eligible(self):
        self.assertTrue(run(reports_leap=False, leap_eligible=False))

    def test_household_already_receiving_leap_is_excluded(self):
        self.assertFalse(run(reports_leap=True, leap_eligible=False))

    def test_household_eligible_for_leap_is_excluded(self):
        """The second half of the union: not receiving it, but would qualify."""
        self.assertFalse(run(reports_leap=False, leap_eligible=True))

    def test_a_reported_benefit_short_circuits_the_calculated_read(self):
        """Already having LEAP settles the exclusion, so an uncalculated cesn_leap is never
        consulted and cannot raise."""
        self.assertFalse(run(reports_leap=True, leap_eligible=None))


class TestUncalculatedLeapRaises(TestCase):
    def test_uncalculated_leap_raises_rather_than_waiving_the_exclusion(self):
        """Tolerating absence here would read as "not LEAP-eligible" and pass the
        exclusion, offering Energy EBT to a household that may well get LEAP. Raising drops
        this program from the results instead, which is the safe direction for a screen-out.
        """
        with self.assertRaises(DependencyError):
            run(reports_leap=False, leap_eligible=None)


class TestDependenciesCoverTheUpstream(TestCase):
    def test_declares_everything_cesn_leap_needs(self):
        """The LEAP exclusion reads cesn_leap's result, so this program must not be
        calculable on a screen where cesn_leap is not. LEAP needs `county` and the income
        test here does not, so without it a county-less screen would drop Energy EBT
        entirely rather than answer for it."""
        uncovered = set(EnergyCalculatorEnergyAssistance.dependencies) - set(EnergyCalculatorEnergyEbt.dependencies)
        self.assertEqual(uncovered, set())

    def test_county_is_declared(self):
        self.assertIn("county", EnergyCalculatorEnergyEbt.dependencies)
