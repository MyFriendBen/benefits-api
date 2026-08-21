"""
`ProgramCalculator.program_eligible` — reads another program's computed result out of
`self.data` by a name the caller supplies.

It replaced the `medicaid_eligible(data)` helper, which walked a tuple of four state
Medicaid keys and returned False when none was present. That conflated "not calculated
yet" with "calculated, and not eligible", and returned False for any state absent from
the tuple. These tests pin the two properties that fixed: only the named program is
consulted, and an absent key raises instead of guessing.
"""

from unittest.mock import Mock

from django.test import SimpleTestCase

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.util import DependencyError


def make_calculator(data):
    return ProgramCalculator(Mock(), Mock(), data, Mock())


def eligibility(is_eligible):
    e = Eligibility()
    e.eligible = is_eligible
    return e


class TestProgramEligibleReadsTheNamedProgram(SimpleTestCase):
    def test_returns_true_when_the_named_program_is_eligible(self):
        calc = make_calculator({"co_medicaid": eligibility(True)})
        self.assertTrue(calc.program_eligible("co_medicaid"))

    def test_returns_false_when_the_named_program_is_not_eligible(self):
        calc = make_calculator({"co_medicaid": eligibility(False)})
        self.assertFalse(calc.program_eligible("co_medicaid"))

    def test_reads_only_the_named_program(self):
        """Two Medicaid results present; the gate must read the one it asked for rather
        than whichever the old tuple happened to list first."""
        calc = make_calculator({"co_medicaid": eligibility(False), "nc_medicaid": eligibility(True)})
        self.assertFalse(calc.program_eligible("co_medicaid"))
        self.assertTrue(calc.program_eligible("nc_medicaid"))


class TestProgramEligibleRaisesRatherThanGuessing(SimpleTestCase):
    def test_absent_key_raises(self):
        calc = make_calculator({})
        with self.assertRaises(DependencyError):
            calc.program_eligible("co_medicaid")

    def test_another_states_result_does_not_satisfy_the_gate(self):
        """The old helper returned nc_medicaid's answer to a Colorado caller because both
        were in one tuple. Naming the program makes that a raise."""
        calc = make_calculator({"nc_medicaid": eligibility(True)})
        with self.assertRaises(DependencyError):
            calc.program_eligible("co_medicaid")

    def test_states_the_old_tuple_omitted_are_readable(self):
        """ma_mass_health and wa_apple_health_medicaid were absent from
        the old helper's state list, so it returned False for them no matter the
        household. Nothing about them is special now."""
        for code in ("ma_mass_health", "wa_apple_health_medicaid"):
            with self.subTest(code=code):
                calc = make_calculator({code: eligibility(True)})
                self.assertTrue(calc.program_eligible(code))


def member(member_id):
    m = Mock()
    m.id = member_id
    return m


def household_with_members(verdicts):
    """An upstream `Eligibility` carrying a per-member verdict, keyed by member id."""
    e = Eligibility()
    for member_id, is_eligible in verdicts.items():
        me = MemberEligibility(member(member_id))
        me.eligible = is_eligible
        e.add_member_eligibility(me)
    return e


class TestMemberProgramEligible(SimpleTestCase):
    """`member_program_eligible` is `program_eligible` at member scope: CFHC excludes a
    member who qualifies for CHP+, which is a per-member verdict, not a household one."""

    def test_returns_the_named_members_verdict(self):
        calc = make_calculator({"chp": household_with_members({1: True, 2: False})})
        self.assertTrue(calc.member_program_eligible("chp", member(1)))
        self.assertFalse(calc.member_program_eligible("chp", member(2)))

    def test_member_absent_from_the_upstream_is_not_eligible(self):
        """The upstream records a verdict for every member it evaluated, so no entry means
        it did not consider them — not eligible, rather than an error."""
        calc = make_calculator({"chp": household_with_members({1: True})})
        self.assertFalse(calc.member_program_eligible("chp", member(99)))

    def test_no_members_evaluated_is_not_eligible(self):
        calc = make_calculator({"chp": Eligibility()})
        self.assertFalse(calc.member_program_eligible("chp", member(1)))

    def test_absent_upstream_raises(self):
        """Same contract as the household form: "not calculated" is not an answer."""
        calc = make_calculator({})
        with self.assertRaises(DependencyError):
            calc.member_program_eligible("chp", member(1))

    def test_reads_the_member_verdict_not_the_household_result(self):
        """A household can fail the upstream's own household test while a member still
        qualifies — CHP+ works exactly that way — so this must not consult
        `Eligibility.eligible`. Reading the household flag would waive cfhc's per-member
        CHP+ exclusion for every member of such a household."""
        upstream = household_with_members({1: True})
        upstream.condition(False)  # the upstream's household test failed
        self.assertFalse(upstream.eligible)

        calc = make_calculator({"chp": upstream})
        self.assertTrue(calc.member_program_eligible("chp", member(1)))

    def test_a_member_is_not_eligible_just_because_the_household_is(self):
        """The mirror: an upstream whose household result is eligible does not make a member
        it judged ineligible eligible."""
        upstream = household_with_members({1: False, 2: True})
        self.assertTrue(upstream.eligible, "sanity: an eligible member makes the household eligible")

        calc = make_calculator({"chp": upstream})
        self.assertFalse(calc.member_program_eligible("chp", member(1)))
        self.assertTrue(calc.member_program_eligible("chp", member(2)))

    def test_another_programs_result_does_not_satisfy_the_gate(self):
        calc = make_calculator({"co_medicaid": household_with_members({1: True})})
        with self.assertRaises(DependencyError):
            calc.member_program_eligible("chp", member(1))


class TestAnyProgramEligible(SimpleTestCase):
    """A presumptive-eligibility list is one of several ways to qualify, so a sibling that
    was not calculated is not an error — unlike a single named dependency."""

    def test_true_when_any_is_eligible(self):
        calc = make_calculator({"cesn_leap": eligibility(True), "cesn_eoc": eligibility(False)})
        self.assertTrue(calc.any_program_eligible(["cesn_eoc", "cesn_leap"]))

    def test_false_when_none_is_eligible(self):
        calc = make_calculator({"cesn_leap": eligibility(False), "cesn_eoc": eligibility(False)})
        self.assertFalse(calc.any_program_eligible(["cesn_leap", "cesn_eoc"]))

    def test_an_uncalculated_sibling_does_not_raise(self):
        """The activation-coupling case: one deactivated row must not drop the caller from
        results when another program in the list already qualifies the household."""
        calc = make_calculator({"cesn_leap": eligibility(True)})
        self.assertTrue(calc.any_program_eligible(["cesn_leap", "cesn_care", "cesn_cowap"]))

    def test_all_absent_is_false_not_a_raise(self):
        calc = make_calculator({})
        self.assertFalse(calc.any_program_eligible(["cesn_leap", "cesn_care"]))

    def test_stops_at_the_first_eligible_program(self):
        """Short-circuits, so a later entry is never consulted once the answer is settled."""
        consulted = []

        class Recording(dict):
            def get(self, key, default=None):
                consulted.append(key)
                return super().get(key, default)

        calc = make_calculator(Recording({"cesn_leap": eligibility(True)}))
        self.assertTrue(calc.any_program_eligible(["cesn_leap", "cesn_care"]))
        self.assertEqual(consulted, ["cesn_leap"])
