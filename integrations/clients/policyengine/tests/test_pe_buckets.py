"""
One screen, more than one PolicyEngine request.

Programs on a screen share one payload, so two that want different values for the same input
cannot both be served by it. That used to raise out of payload assembly uncaught and 500
`/api/eligibility/{id}`, losing every program's results over one program's disagreement
`calc_pe_eligibility` now sends one request per group of programs that agree and merges the
results, so a disagreement costs a round trip instead of the response.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from benefits.tests.cache_override import LOCAL_CACHE
from integrations.clients.policyengine import policy_engine as pe
from programs.framework.pe_dependencies.base import Member
from programs.framework.pe_dependencies.payload import build_pe_input
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


def sent_payloads(log):
    """Fake engine that records the payload it was handed. Constructed once per request, so
    the log is the request count as well as the request bodies."""

    class _Engine:
        method_name = "Fake Policy Engine API"

        def __init__(self, data):
            log.append(data)
            self.request_payload = data
            self.response_json = {"result": {}}

    return _Engine


@override_settings(CACHES=LOCAL_CACHE)
class PeBucketTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")

    def setUp(self):
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="65101",
            county="Cole County",
            household_size=1,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        self.head_id = str(self.head.id)

    def calculator(self, inputs):
        calc = MagicMock()
        calc.can_calc.return_value = True
        calc.pe_inputs = list(inputs)
        calc.pe_outputs = []
        calc.pe_monthly_outputs = []
        calc.pe_period = PERIOD
        return calc

    def run_eligibility(self, calculators, max_buckets=None):
        """Run the real payload build and bucket loop against a fake engine.

        `all_eligibility` is faked to report whichever programs it was handed, which is how
        these assert that each request answered the right programs.
        """
        log = []
        patches = [
            patch.object(pe, "pe_engines", [sent_payloads(log)]),
            patch.object(pe, "all_eligibility", side_effect=lambda sim, programs: dict.fromkeys(programs, "ok")),
            patch.object(pe, "capture_message"),
        ]
        if max_buckets is not None:
            patches.append(
                patch.object(
                    pe,
                    "build_pe_input",
                    side_effect=lambda *args, **kwargs: build_pe_input(*args, **{**kwargs, "max_buckets": max_buckets}),
                )
            )

        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in patches])

        return pe.calc_pe_eligibility(self.screen, calculators), log

    def ages(self, payload):
        return payload["household"]["people"][self.head_id]["age"]


class TestProgramsThatAgree(PeBucketTestBase):
    def test_one_request_answers_every_program(self):
        result, log = self.run_eligibility({"a": self.calculator([FortyYearOld]), "b": self.calculator([FortyYearOld])})

        self.assertEqual(len(log), 1)
        self.assertEqual(sorted(result["eligibility"]), ["a", "b"])

    def test_the_response_shape_is_unchanged(self):
        """Every screen returns this shape; only a split screen adds to it."""
        result, _ = self.run_eligibility({"a": self.calculator([FortyYearOld])})

        self.assertEqual(sorted(result["_pe_data"]), ["request", "response"])


class TestProgramsThatDisagree(PeBucketTestBase):
    def setUp(self):
        super().setUp()
        self.result, self.log = self.run_eligibility(
            {
                "agrees_one": self.calculator([FortyYearOld]),
                "disagrees": self.calculator([FortyOneYearOld]),
                "agrees_two": self.calculator([FortyYearOld]),
            }
        )

    def test_every_program_still_gets_a_result(self):
        """The regression this exists for: one program's disagreement used to cost all of
        them their results."""
        self.assertEqual(sorted(self.result["eligibility"]), ["agrees_one", "agrees_two", "disagrees"])

    def test_it_took_two_requests(self):
        self.assertEqual(len(self.log), 2)

    def test_each_request_carried_the_value_its_programs_wanted(self):
        self.assertEqual([self.ages(payload) for payload in self.log], [{PERIOD: 40}, {PERIOD: 41}])

    def test_the_extra_request_is_reported_for_admins(self):
        self.assertEqual(len(self.result["_pe_data"]["additional_requests"]), 1)
        self.assertEqual(self.ages(self.result["_pe_data"]["request"]), {PERIOD: 40})
        self.assertEqual(self.ages(self.result["_pe_data"]["additional_requests"][0]["request"]), {PERIOD: 41})


class TestTheDisagreementIsReported(PeBucketTestBase):
    def test_it_logs_the_split_and_both_values(self):
        log = []
        with patch.object(pe, "pe_engines", [sent_payloads(log)]), patch.object(
            pe, "all_eligibility", side_effect=lambda sim, programs: dict.fromkeys(programs, "ok")
        ), patch.object(pe, "capture_message") as capture_message:
            pe.calc_pe_eligibility(
                self.screen,
                {
                    "wants_forty": self.calculator([FortyYearOld]),
                    "wants_forty_one": self.calculator([FortyOneYearOld]),
                },
            )

        warnings = [c for c in capture_message.call_args_list if c.kwargs.get("level") == "warning"]
        self.assertEqual(len(warnings), 1)
        message = warnings[0].args[0]
        for expected in ("age", "40", "41", "wants_forty", "wants_forty_one", "2 request"):
            self.assertIn(expected, message)


class TestPastTheRequestLimit(PeBucketTestBase):
    def test_the_unserved_program_has_no_result(self):
        """Bounded splitting means some screen shapes lose a program. It is reported absent,
        which the caller already handles, rather than answered with a value it did not ask
        for."""
        result, log = self.run_eligibility(
            {
                "a": self.calculator([FortyYearOld]),
                "b": self.calculator([FortyOneYearOld]),
                "c": self.calculator([FortyTwoYearOld]),
            },
            max_buckets=2,
        )

        self.assertEqual(len(log), 2)
        self.assertEqual(sorted(result["eligibility"]), ["a", "b"])


class TestOneRequestFailing(PeBucketTestBase):
    def test_the_other_request_still_returns(self):
        """Contained per request: PolicyEngine failing the second call no longer costs the
        first call's programs their results."""
        log = []
        engine = sent_payloads(log)

        class _FailsTheSecond(engine):
            def __init__(self, data):
                super().__init__(data)
                if len(log) == 2:
                    raise RuntimeError("boom")

        with patch.object(pe, "pe_engines", [_FailsTheSecond]), patch.object(
            pe, "all_eligibility", side_effect=lambda sim, programs: dict.fromkeys(programs, "ok")
        ), patch.object(pe, "capture_message"), patch.object(pe, "capture_exception"), patch.object(
            pe, "record_external_api_failure"
        ):
            result = pe.calc_pe_eligibility(
                self.screen,
                {
                    "served": self.calculator([FortyYearOld]),
                    "unserved": self.calculator([FortyOneYearOld]),
                },
            )

        self.assertEqual(sorted(result["eligibility"]), ["served"])
