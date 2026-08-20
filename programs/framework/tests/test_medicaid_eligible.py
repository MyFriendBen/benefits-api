"""
`ProgramCalculator.medicaid_eligible` — the named-dependency gate that replaced the
`medicaid_eligible(data)` helper.

The helper walked a tuple of four state Medicaid keys and returned False when none was
present, which conflated "not calculated yet" with "calculated, and not eligible" and
returned False for any state absent from that tuple. These tests pin the two properties
that fixed: the caller's own program code is the only key consulted, and an absent key
raises instead of guessing.
"""

from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.framework.base import Eligibility, ProgramCalculator
from programs.util import DependencyError


def make_calculator(data):
    return ProgramCalculator(Mock(), Mock(), data, Mock())


def eligibility(is_eligible):
    e = Eligibility()
    e.eligible = is_eligible
    return e


class TestMedicaidEligibleReadsTheNamedProgram(SimpleTestCase):
    def test_returns_true_when_the_named_program_is_eligible(self):
        calc = make_calculator({"co_medicaid": eligibility(True)})
        self.assertTrue(calc.medicaid_eligible("co_medicaid"))

    def test_returns_false_when_the_named_program_is_not_eligible(self):
        calc = make_calculator({"co_medicaid": eligibility(False)})
        self.assertFalse(calc.medicaid_eligible("co_medicaid"))

    def test_reads_only_the_named_program(self):
        """Two Medicaid results present; the gate must read the one it asked for rather
        than whichever the old tuple happened to list first."""
        calc = make_calculator({"co_medicaid": eligibility(False), "nc_medicaid": eligibility(True)})
        self.assertFalse(calc.medicaid_eligible("co_medicaid"))
        self.assertTrue(calc.medicaid_eligible("nc_medicaid"))


class TestMedicaidEligibleRaisesRatherThanGuessing(SimpleTestCase):
    def test_absent_key_raises(self):
        calc = make_calculator({})
        with self.assertRaises(DependencyError):
            calc.medicaid_eligible("co_medicaid")

    def test_another_states_result_does_not_satisfy_the_gate(self):
        """The old helper returned nc_medicaid's answer to a Colorado caller because both
        were in one tuple. Naming the program makes that a raise."""
        calc = make_calculator({"nc_medicaid": eligibility(True)})
        with self.assertRaises(DependencyError):
            calc.medicaid_eligible("co_medicaid")

    def test_states_the_old_tuple_omitted_are_readable(self):
        """ma_mass_health and wa_apple_health_medicaid were absent from
        STATE_MEDICAID_OPTIONS, so the old helper returned False for them no matter the
        household. Nothing about them is special now."""
        for code in ("ma_mass_health", "wa_apple_health_medicaid"):
            with self.subTest(code=code):
                calc = make_calculator({code: eligibility(True)})
                self.assertTrue(calc.medicaid_eligible(code))
