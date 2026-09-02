"""
What payload assembly does when two programs want different values for the same input.

One PolicyEngine request carries every program on a screen, so a slot -- a field, at a
period, for a member -- holds one value. Two programs disagreeing about it used to raise out
of `pe_input` uncaught and 500 the whole eligibility response, losing 34 programs' results
over one program's disagreement.

Now the disagreement splits the screen: the value most programs asked for goes in the union
payload, and the programs that wanted something else are answered by a second request
carrying the same payload with only the contradicted slot rewritten. The two properties that
matter are that the union payload is exactly what an agreeing screen would have sent, and
that a program on the losing side still sees every other input the screen produced.
"""

from django.test import TestCase, override_settings

from benefits.tests.cache_override import LOCAL_CACHE
from programs.framework.pe_dependencies.base import ConflictingDependencyError, Household, Member
from programs.framework.pe_dependencies.payload import (
    Contribution,
    Slot,
    _values_for,
    bucket_payload,
    build_pe_input,
    pe_input,
)
from screener.models import HouseholdMember, Screen, WhiteLabel

PERIOD = "2026"


class FortyYearOld(Member):
    field = "age"

    def value(self):
        return 40


class FortyOneYearOld(Member):
    field = "age"

    def value(self):
        return 41


class FortyTwoYearOld(Member):
    field = "age"

    def value(self):
        return 42


class Pregnant(Member):
    field = "is_pregnant"

    def value(self):
        return True


class StateCode(Household):
    field = "state_code"

    def value(self):
        return "TX"


def fake_program(code, inputs):
    """A calculator-shaped stand-in.

    A class rather than an instance, as the other payload tests use: `pe_period` is a
    property that needs a configured ``Program.year``, and these tests are about which value
    reaches a slot, not about where the period came from.
    """
    return type(
        code,
        (),
        {
            "program_code": code,
            "pe_inputs": list(inputs),
            "pe_outputs": [],
            "pe_monthly_outputs": [],
            "pe_period": PERIOD,
        },
    )


@override_settings(CACHES=LOCAL_CACHE)
class PayloadConflictTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")

    def setUp(self):
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Travis County",
            household_size=1,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        self.head_id = str(self.head.id)

    def ages(self, payload):
        return payload["household"]["people"][self.head_id]["age"]


class TestProgramsThatAgree(PayloadConflictTestBase):
    """The overwhelming majority of screens: nothing to resolve, nothing to split."""

    def test_one_bucket_holding_every_program(self):
        plan = build_pe_input(
            self.screen,
            [fake_program("a", [FortyYearOld]), fake_program("b", [FortyYearOld, Pregnant])],
        )

        self.assertEqual([bucket.program_indexes for bucket in plan.buckets], [[0, 1]])
        self.assertEqual(plan.conflicts, [])
        self.assertEqual(plan.dropped_program_indexes, [])

    def test_the_payload_is_what_the_programs_asked_for(self):
        plan = build_pe_input(self.screen, [fake_program("a", [FortyYearOld, Pregnant])])

        person = plan.payload["household"]["people"][self.head_id]
        self.assertEqual(person["age"], {PERIOD: 40})
        self.assertEqual(person["is_pregnant"], {PERIOD: True})

    def test_a_program_repeating_a_dependency_is_not_a_disagreement(self):
        """`pe_inputs` lists are assembled from shared groups, so the same class can appear
        more than once in one program. It agrees with itself."""
        plan = build_pe_input(self.screen, [fake_program("a", [FortyYearOld, FortyYearOld])])

        self.assertEqual([bucket.program_indexes for bucket in plan.buckets], [[0]])
        self.assertEqual(self.ages(plan.payload), {PERIOD: 40})

    def test_bucket_payload_is_the_union_payload_itself(self):
        """No copy when there is nothing to override — the same object goes to the wire."""
        plan = build_pe_input(self.screen, [fake_program("a", [FortyYearOld])])

        self.assertIs(bucket_payload(plan, plan.buckets[0]), plan.payload)


class TestTheMajorityValueWins(PayloadConflictTestBase):
    def setUp(self):
        super().setUp()
        self.programs = [
            fake_program("agrees_one", [FortyYearOld]),
            fake_program("disagrees", [FortyOneYearOld]),
            fake_program("agrees_two", [FortyYearOld]),
        ]
        self.plan = build_pe_input(self.screen, self.programs)

    def test_the_union_payload_holds_the_value_most_programs_wanted(self):
        self.assertEqual(self.ages(self.plan.payload), {PERIOD: 40})

    def test_the_disagreeing_program_is_deferred_to_its_own_request(self):
        self.assertEqual([bucket.program_indexes for bucket in self.plan.buckets], [[0, 2], [1]])

    def test_the_second_request_carries_the_value_that_program_wanted(self):
        payload = bucket_payload(self.plan, self.plan.buckets[1])

        self.assertEqual(self.ages(payload), {PERIOD: 41})

    def test_the_first_request_is_unaffected_by_the_second(self):
        bucket_payload(self.plan, self.plan.buckets[1])

        self.assertEqual(self.ages(self.plan.payload), {PERIOD: 40})

    def test_nothing_is_dropped(self):
        self.assertEqual(self.plan.dropped_program_indexes, [])


class TestTheSecondRequestSeesTheWholeHousehold(PayloadConflictTestBase):
    """The point of splitting rather than rebuilding: a program that disagrees about one
    field is not thereby cut off from every input the rest of the screen produced."""

    def test_it_keeps_inputs_it_never_declared(self):
        plan = build_pe_input(
            self.screen,
            [
                fake_program("a", [FortyYearOld, Pregnant, StateCode]),
                fake_program("b", [FortyYearOld]),
                fake_program("disagrees", [FortyOneYearOld]),
            ],
        )
        payload = bucket_payload(plan, plan.buckets[1])

        self.assertEqual(payload["household"]["people"][self.head_id]["is_pregnant"], {PERIOD: True})
        self.assertEqual(payload["household"]["households"]["household"]["state_code"], {PERIOD: "TX"})

    def test_only_the_contradicted_slot_differs(self):
        plan = build_pe_input(
            self.screen,
            [
                fake_program("a", [FortyYearOld, Pregnant]),
                fake_program("b", [FortyYearOld]),
                fake_program("disagrees", [FortyOneYearOld, Pregnant]),
            ],
        )

        self.assertEqual(
            list(plan.buckets[1].overrides),
            [Slot("people", self.head_id, "age", PERIOD)],
        )

    def test_an_input_only_the_second_request_asked_for_reaches_both(self):
        """A slot nobody disagreed about is written from whichever program contributed it,
        even one deferred to a later request — PolicyEngine ignores inputs the programs in
        front of it don't read."""
        plan = build_pe_input(
            self.screen,
            [
                fake_program("a", [FortyYearOld]),
                fake_program("b", [FortyYearOld]),
                fake_program("disagrees", [FortyOneYearOld, Pregnant]),
            ],
        )

        self.assertEqual(plan.payload["household"]["people"][self.head_id]["is_pregnant"], {PERIOD: True})
        self.assertEqual(
            bucket_payload(plan, plan.buckets[1])["household"]["people"][self.head_id]["is_pregnant"],
            {PERIOD: True},
        )


class TestTies(PayloadConflictTestBase):
    def test_a_tie_goes_to_the_program_iterated_first(self):
        """Two programs, two values, no majority. Registry order decides, which is only
        acceptable because it is the tie — any rule has to pick something."""
        plan = build_pe_input(
            self.screen,
            [fake_program("first", [FortyOneYearOld]), fake_program("second", [FortyYearOld])],
        )

        self.assertEqual(self.ages(plan.payload), {PERIOD: 41})
        self.assertEqual([bucket.program_indexes for bucket in plan.buckets], [[0], [1]])


class TestThreeWayDisagreement(PayloadConflictTestBase):
    def test_each_distinct_value_gets_a_request(self):
        plan = build_pe_input(
            self.screen,
            [
                fake_program("a", [FortyYearOld]),
                fake_program("b", [FortyYearOld]),
                fake_program("c", [FortyOneYearOld]),
                fake_program("d", [FortyTwoYearOld]),
            ],
        )

        self.assertEqual([bucket.program_indexes for bucket in plan.buckets], [[0, 1], [2], [3]])
        self.assertEqual(
            [self.ages(bucket_payload(plan, bucket)) for bucket in plan.buckets],
            [{PERIOD: 40}, {PERIOD: 41}, {PERIOD: 42}],
        )
        self.assertEqual(plan.dropped_program_indexes, [])


class TestTheRequestLimit(PayloadConflictTestBase):
    def test_programs_past_the_limit_are_dropped_not_served(self):
        """Splitting is bounded: each bucket is an HTTP round trip. Past the limit the
        remaining programs get no result, which the caller reports as missing rather than
        answering them with a value their rule doesn't mean."""
        plan = build_pe_input(
            self.screen,
            [
                fake_program("a", [FortyYearOld]),
                fake_program("b", [FortyOneYearOld]),
                fake_program("c", [FortyTwoYearOld]),
            ],
            max_buckets=2,
        )

        self.assertEqual([bucket.program_indexes for bucket in plan.buckets], [[0], [1]])
        self.assertEqual(plan.dropped_program_indexes, [2])

    def test_a_dropped_program_is_named_in_the_report(self):
        plan = build_pe_input(
            self.screen,
            [fake_program("kept", [FortyYearOld]), fake_program("dropped", [FortyOneYearOld])],
            max_buckets=1,
        )

        self.assertEqual([bucket.program_indexes for bucket in plan.buckets], [[0]])
        self.assertEqual(plan.dropped_program_indexes, [1])
        self.assertTrue(plan.conflicts)


class TestTheConflictReport(PayloadConflictTestBase):
    def test_it_names_the_slot_both_values_and_who_wanted_each(self):
        plan = build_pe_input(
            self.screen,
            [fake_program("wants_forty", [FortyYearOld]), fake_program("wants_forty_one", [FortyOneYearOld])],
        )

        self.assertEqual(len(plan.conflicts), 1)
        report = plan.conflicts[0]
        for expected in ("age", PERIOD, self.head_id, "40", "41", "wants_forty", "wants_forty_one"):
            self.assertIn(expected, report)

    def test_an_agreeing_screen_reports_nothing(self):
        plan = build_pe_input(self.screen, [fake_program("a", [FortyYearOld])])

        self.assertEqual(plan.conflicts, [])


class TestTheWriteInvariant(PayloadConflictTestBase):
    """`_values_for` is the assertion that partitioning worked. It is unreachable through
    `build_pe_input`; a raise from it would mean the partition handed one request two values
    for one slot, which is a bug in the partition rather than a fact about the screen."""

    def test_disagreement_inside_one_bucket_raises(self):
        slot = Slot("people", self.head_id, "age", PERIOD)
        contributions = [Contribution(slot, 40, 0), Contribution(slot, 41, 1)]

        with self.assertRaises(ConflictingDependencyError) as raised:
            _values_for(contributions, [0, 1])

        self.assertEqual(raised.exception.field, "age")
        self.assertEqual({raised.exception.value_1, raised.exception.value_2}, {40, 41})
        self.assertEqual(raised.exception.period, PERIOD)
        self.assertEqual(raised.exception.member, self.head_id)

    def test_the_message_distinguishes_it_from_a_missing_dependency(self):
        error = ConflictingDependencyError("age", 1, 0, period=PERIOD, member="7")

        self.assertIn("Conflicting", str(error))
        self.assertIn("age at 2026 for member 7", str(error))


class TestPeInputStillReturnsThePayload(PayloadConflictTestBase):
    """`pe_input` is what a hundred payload tests and the spec-scenario harness call. It
    keeps returning the union payload, so splitting is invisible to callers that only ever
    send one request."""

    def test_it_returns_the_union_payload(self):
        programs = [fake_program("a", [FortyYearOld]), fake_program("b", [FortyOneYearOld])]

        self.assertEqual(pe_input(self.screen, programs), build_pe_input(self.screen, programs).payload)
