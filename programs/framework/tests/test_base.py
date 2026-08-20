"""The eligibility protocol every calculator runs through.

`Eligibility` accumulates a program's verdict, `MemberEligibility` a single member's,
and `ProgramCalculator` orchestrates the two. A regression here moves dollar amounts
for every program in every white label, and would surface as one program's test
failing for reasons that look like that program's own bug.

The calculators defined below are minimal stand-ins. They exist to exercise the
base's orchestration, not to model any real benefit.
"""

import datetime

from django.test import TestCase

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
from programs.util import Dependencies, DependencyError
from screener.models import HouseholdMember, Screen, WhiteLabel


class MemberEligibilityTests(TestCase):
    """A single member's verdict."""

    def test_starts_eligible_with_no_value(self):
        """The default is eligible: a calculator narrows, it does not admit."""
        m = MemberEligibility(member=None)

        self.assertTrue(m.eligible)
        self.assertEqual(m.value, 0)

    def test_a_failing_condition_makes_it_ineligible(self):
        m = MemberEligibility(member=None)

        m.condition(False)

        self.assertFalse(m.eligible)

    def test_a_passing_condition_leaves_it_eligible(self):
        m = MemberEligibility(member=None)

        m.condition(True)

        self.assertTrue(m.eligible)

    def test_eligibility_does_not_recover(self):
        """Once a condition fails, a later passing one must not undo it."""
        m = MemberEligibility(member=None)

        m.condition(False)
        m.condition(True)

        self.assertFalse(m.eligible)


class EligibilityConditionTests(TestCase):
    """`condition()` drives both the verdict and the explanation shown to a user."""

    def test_starts_eligible_with_no_messages(self):
        e = Eligibility()

        self.assertTrue(e.eligible)
        self.assertEqual(e.pass_messages, [])
        self.assertEqual(e.fail_messages, [])

    def test_a_failing_condition_with_a_message_records_it(self):
        e = Eligibility()

        e.condition(False, "must be over 18")

        self.assertFalse(e.eligible)
        self.assertEqual(e.fail_messages, ["must be over 18"])
        self.assertEqual(e.pass_messages, [])

    def test_a_passing_condition_with_a_message_records_it(self):
        e = Eligibility()

        e.condition(True, "is a resident")

        self.assertTrue(e.eligible)
        self.assertEqual(e.pass_messages, ["is a resident"])
        self.assertEqual(e.fail_messages, [])

    def test_a_failing_condition_without_a_message_is_silent(self):
        """Eligibility drops with nothing to show the user.

        Deliberate — some rules have no user-facing explanation — but it means a
        household can be ineligible with an empty `fail_messages`, so a caller
        cannot assume a reason exists.
        """
        e = Eligibility()

        e.condition(False)

        self.assertFalse(e.eligible)
        self.assertEqual(e.fail_messages, [])

    def test_a_passing_condition_without_a_message_records_nothing(self):
        e = Eligibility()

        e.condition(True)

        self.assertTrue(e.eligible)
        self.assertEqual(e.pass_messages, [])

    def test_eligibility_does_not_recover(self):
        e = Eligibility()

        e.condition(False, "failed")
        e.condition(True, "passed")

        self.assertFalse(e.eligible)
        self.assertEqual(e.fail_messages, ["failed"])
        self.assertEqual(e.pass_messages, ["passed"])

    def test_failed_and_passed_can_be_called_directly(self):
        """Calculators reach for these when the verdict is already known."""
        e = Eligibility()

        e.passed("first")
        e.failed("second")

        self.assertFalse(e.eligible)
        self.assertEqual(e.pass_messages, ["first"])
        self.assertEqual(e.fail_messages, ["second"])


class EligibilityValueTests(TestCase):
    """`value` is the number a household sees, summed across household and members."""

    def test_value_is_zero_by_default(self):
        self.assertEqual(Eligibility().value, 0)

    def test_value_is_the_household_amount_when_no_members_are_added(self):
        e = Eligibility()
        e.household_value = 1_200

        self.assertEqual(e.value, 1_200)

    def test_value_sums_the_household_and_every_stored_member(self):
        e = Eligibility()
        e.household_value = 100

        for amount in (10, 20, 30):
            m = MemberEligibility(member=None)
            m.value = amount
            e.add_member_eligibility(m)

        self.assertEqual(e.value, 160)

    def test_the_sum_does_not_filter_on_member_eligibility(self):
        """`value` adds up what it was given.

        The filtering happens earlier, in `ProgramCalculator.value()`, which assigns
        an amount only to eligible members. A value set on an ineligible member is a
        caller error, and this pins that the sum does not quietly absorb it.
        """
        e = Eligibility()
        m = MemberEligibility(member=None)
        m.condition(False)
        m.value = 500
        e.add_member_eligibility(m)

        self.assertEqual(e.value, 500)

    def test_add_member_eligibility_keeps_every_member(self):
        """Eligible and ineligible members are both stored, because
        `household_eligible` runs afterwards and reads them."""
        e = Eligibility()
        eligible, ineligible = MemberEligibility(None), MemberEligibility(None)
        ineligible.condition(False)

        e.add_member_eligibility(eligible)
        e.add_member_eligibility(ineligible)

        self.assertEqual(e.eligible_members, [eligible, ineligible])


class ProgramCalculatorTestCase(TestCase):
    """A three-person household for the orchestration tests below."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Test", code="test", state_code="TS")

    def setUp(self):
        self.screen = Screen.objects.create(
            white_label=self.white_label, household_size=2, completed=False, is_test=True
        )
        HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", birth_year_month=datetime.date(1990, 1, 1)
        )
        HouseholdMember.objects.create(
            screen=self.screen, relationship="child", birth_year_month=datetime.date(2018, 1, 1)
        )

    def calculator(self, cls, missing=()):
        return cls(self.screen, None, {}, Dependencies(missing))


class ProgramCalculatorEligibleTests(ProgramCalculatorTestCase):
    """`eligible()` walks the members, then the household."""

    def test_a_calculator_that_asserts_nothing_is_eligible(self):
        class Everyone(ProgramCalculator):
            pass

        e = self.calculator(Everyone).eligible()

        self.assertTrue(e.eligible)
        self.assertEqual(len(e.eligible_members), 2)

    def test_the_household_is_ineligible_when_no_member_qualifies(self):
        """A program with per-member rules needs at least one member to pass."""

        class NoOne(ProgramCalculator):
            def member_eligible(self, e: MemberEligibility):
                e.condition(False)

        e = self.calculator(NoOne).eligible()

        self.assertFalse(e.eligible)

    def test_one_qualifying_member_is_enough(self):
        class OnlyChildren(ProgramCalculator):
            def member_eligible(self, e: MemberEligibility):
                e.condition(e.member.relationship == "child")

        e = self.calculator(OnlyChildren).eligible()

        self.assertTrue(e.eligible)
        self.assertEqual([m.eligible for m in e.eligible_members], [False, True])

    def test_household_eligible_runs_after_the_members(self):
        """The ordering is load-bearing: a household rule may read member results."""
        seen = []

        class CountsEligibleMembers(ProgramCalculator):
            def member_eligible(self, e: MemberEligibility):
                e.condition(e.member.relationship == "child")

            def household_eligible(self, e: Eligibility):
                seen.extend(m.eligible for m in e.eligible_members)

        self.calculator(CountsEligibleMembers).eligible()

        self.assertEqual(seen, [False, True])

    def test_a_failing_household_rule_overrides_eligible_members(self):
        class HouseholdSaysNo(ProgramCalculator):
            def household_eligible(self, e: Eligibility):
                e.condition(False, "household rule")

        e = self.calculator(HouseholdSaysNo).eligible()

        self.assertFalse(e.eligible)
        self.assertEqual(e.fail_messages, ["household rule"])


class ProgramCalculatorValueTests(ProgramCalculatorTestCase):
    """`value()` fills in amounts, and only for an eligible household."""

    class Paying(ProgramCalculator):
        amount = 1_000
        member_amount = 50

    def test_an_eligible_household_gets_the_household_and_member_amounts(self):
        calc = self.calculator(self.Paying)
        e = calc.eligible()

        calc.value(e)

        self.assertEqual(e.household_value, 1_000)
        self.assertEqual(e.value, 1_100)

    def test_an_ineligible_household_is_left_at_zero(self):
        """`value()` returns early, so nothing is computed for a household that
        has already failed."""

        class PayingButIneligible(ProgramCalculatorValueTests.Paying):
            def household_eligible(self, e: Eligibility):
                e.condition(False)

        calc = self.calculator(PayingButIneligible)
        e = calc.eligible()

        calc.value(e)

        self.assertEqual(e.household_value, 0)
        self.assertEqual(e.value, 0)

    def test_only_eligible_members_are_paid(self):
        class PayingChildrenOnly(ProgramCalculatorValueTests.Paying):
            def member_eligible(self, e: MemberEligibility):
                e.condition(e.member.relationship == "child")

        calc = self.calculator(PayingChildrenOnly)
        e = calc.eligible()

        calc.value(e)

        self.assertEqual([m.value for m in e.eligible_members], [0, 50])
        self.assertEqual(e.value, 1_050)


class ProgramCalculatorCalcTests(ProgramCalculatorTestCase):
    """`calc()` is the entry point: gate on dependencies, then eligibility and value."""

    class NeedsAge(ProgramCalculator):
        dependencies = ("age",)
        amount = 400

    def test_calc_returns_eligibility_with_the_value_applied(self):
        e = self.calculator(self.NeedsAge).calc()

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 400)

    def test_calc_raises_when_a_declared_dependency_is_missing(self):
        """The program is skipped rather than reported at a wrong value."""
        with self.assertRaises(DependencyError):
            self.calculator(self.NeedsAge, missing=("age",)).calc()

    def test_an_undeclared_missing_dependency_does_not_block(self):
        calc = self.calculator(self.NeedsAge, missing=("income",))

        self.assertTrue(calc.can_calc())

    def test_a_calculator_declaring_nothing_can_always_calc(self):
        class NeedsNothing(ProgramCalculator):
            pass

        calc = self.calculator(NeedsNothing, missing=("age", "income"))

        self.assertTrue(calc.can_calc())
