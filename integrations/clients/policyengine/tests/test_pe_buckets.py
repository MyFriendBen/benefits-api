"""
One screen, more than one PolicyEngine request.

Programs on a screen share one payload, so two that want different values for the same input
cannot both be served by it. That used to raise out of payload assembly uncaught and 500
`/api/eligibility/{id}`, losing every program's results over one program's disagreement
`calc_pe_eligibility` now sends one request per group of programs that agree and merges the
results, so a disagreement costs a round trip instead of the response.
"""

import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

import programs.framework.pe_dependencies as dependency
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

    def calculator(self, inputs, period=PERIOD):
        calc = MagicMock()
        calc.can_calc.return_value = True
        calc.pe_inputs = list(inputs)
        calc.pe_outputs = []
        calc.pe_monthly_outputs = []
        calc.pe_period = period
        return calc

    def run_reported(self, calculators):
        """Run the bucket loop and hand back both reporting channels for inspection."""
        log = []
        with patch.object(pe, "pe_engines", [sent_payloads(log)]), patch.object(
            pe, "all_eligibility", side_effect=lambda sim, programs: dict.fromkeys(programs, "ok")
        ), patch.object(pe, "capture_message") as capture_message, patch.object(pe, "logger") as logger:
            result = pe.calc_pe_eligibility(self.screen, calculators)

        warnings = [c for c in capture_message.call_args_list if c.kwargs.get("level") == "warning"]
        return result, log, warnings, logger

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
    def warning_message(self):
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
        return warnings[0].args[0]

    def test_it_names_the_slot_the_split_and_the_programs(self):
        message = self.warning_message()

        for expected in ("age", "wants_forty", "wants_forty_one", "2 request"):
            self.assertIn(expected, message)

    def test_it_does_not_send_the_household_values_to_sentry(self):
        """A conflicting slot holds screener data about a real household. What disagreed is
        actionable; what the household reported is not, and Sentry has no scrubbing
        configured."""
        message = self.warning_message()

        self.assertNotIn("40", message)
        self.assertNotIn("41", message)


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


class TestAnExpectedDisagreementIsNotAnAlert(PeBucketTestBase):
    """`mo_pts` against every other Missouri program. The two age bases disagree by design
    and on a large recurring share of MO traffic, so a Sentry warning per screen would be a
    permanently-firing issue burying the disagreements that mean something. It still splits,
    still answers both programs, and still gets recorded -- in the log."""

    def setUp(self):
        super().setUp()
        # The claim year sits years ahead of the screening date so the two bases disagree
        # whichever month the suite runs in. Pinning a birth month would agree every December.
        self.head.birth_year_month = datetime.date(1961, 6, 1)
        self.head.save()

    def test_the_two_age_bases_are_logged_rather_than_captured(self):
        result, log, warnings, logger = self.run_reported(
            {
                "screening_date_age": self.calculator([dependency.member.AgeDependency], period="2030"),
                "claim_year_age": self.calculator([dependency.member.AgeAtEndOfClaimYearDependency], period="2030"),
            }
        )

        self.assertEqual(len(log), 2)
        self.assertEqual(sorted(result["eligibility"]), ["claim_year_age", "screening_date_age"])
        self.assertEqual(warnings, [])
        self.assertEqual(logger.info.call_count, 1)

    def test_an_unrecognised_disagreement_still_raises(self):
        _, _, warnings, logger = self.run_reported(
            {"wants_forty": self.calculator([FortyYearOld]), "wants_forty_one": self.calculator([FortyOneYearOld])}
        )

        self.assertEqual(len(warnings), 1)
        self.assertEqual(logger.info.call_count, 0)


class TestAProgramThatContradictsItself(PeBucketTestBase):
    """One program declaring two dependencies that write one field with different values. No
    payload can serve it, so it is dropped -- where forcing it into a bucket of its own would
    raise out of payload assembly and cost every PolicyEngine program on the screen."""

    def test_it_is_dropped_and_every_other_program_still_answers(self):
        result, log, warnings, _ = self.run_reported(
            {
                "healthy": self.calculator([FortyYearOld]),
                "contradicts_itself": self.calculator([FortyYearOld, FortyOneYearOld]),
            }
        )

        self.assertEqual(len(log), 1)
        self.assertEqual(sorted(result["eligibility"]), ["healthy"])
        self.assertEqual(len(warnings), 1)
        self.assertIn("contradicts_itself", warnings[0].args[0])


class TestTheTimeBudget(PeBucketTestBase):
    """MAX_PAYLOAD_BUCKETS bounds how many requests a split costs; the budget bounds how long
    they take. Three slow-but-not-failing PolicyEngine calls outlast the gunicorn worker
    timeout, and a killed worker loses the whole response -- including the custom calculators
    that never needed PolicyEngine, which is worse than the degraded result splitting buys."""

    def spent_budget(self):
        return patch.object(pe, "PE_BUCKET_TIME_BUDGET_SECONDS", -1)

    def test_the_first_request_always_goes_out(self):
        """It is what an unsplit screen would have sent, so a spent budget must not cost a
        screen the results it would have had without splitting."""
        with self.spent_budget():
            result, log = self.run_eligibility({"only": self.calculator([FortyYearOld])})

        self.assertEqual(len(log), 1)
        self.assertEqual(sorted(result["eligibility"]), ["only"])

    def test_a_later_request_is_abandoned_once_the_budget_is_spent(self):
        with self.spent_budget():
            result, log = self.run_eligibility(
                {"first": self.calculator([FortyYearOld]), "second": self.calculator([FortyOneYearOld])}
            )

        self.assertEqual(len(log), 1)
        self.assertEqual(sorted(result["eligibility"]), ["first"])

    def test_the_abandoned_programs_are_named(self):
        with self.spent_budget():
            _, _, warnings, _ = self.run_reported(
                {"first": self.calculator([FortyYearOld]), "second": self.calculator([FortyOneYearOld])}
            )

        deadline = [c for c in warnings if "out of time" in c.args[0]]
        self.assertEqual(len(deadline), 1)
        self.assertIn("second", deadline[0].args[0])

    def test_a_split_screen_within_budget_sends_both(self):
        result, log = self.run_eligibility(
            {"first": self.calculator([FortyYearOld]), "second": self.calculator([FortyOneYearOld])}
        )

        self.assertEqual(len(log), 2)
        self.assertEqual(sorted(result["eligibility"]), ["first", "second"])


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
