"""Locks the three ways a degraded eligibility run must reach `missing_programs`.

`missing_programs` is the only signal the response carries that results are incomplete.
It used to be set for exactly two reasons — a DependencyError from a custom calculator,
or a PolicyEngine program absent from the PE result — which left three degradations
completely silent: an external integration (HUD) failing under a calculator that
swallows the error, a calculator crashing on data the dependency gate let through, and
screen data that is malformed rather than null. These tests pin all of them.
"""

from unittest.mock import patch

from django.test import TestCase

from integrations.clients.hud_income_limits import hud_client
from integrations.external_api_status import HUD, record_external_api_failure, track_external_api_failures
from programs.models import (
    Program,
    ProgramCategory,
    UrgentNeed,
    UrgentNeedCategory,
    UrgentNeedFunction,
    UrgentNeedType,
    WarningMessage,
)
from programs.programs.calc import Eligibility, ProgramCalculator
from programs.programs.urgent_needs.base import UrgentNeedFunction as UrgentNeedFunctionCalculator
from programs.util import DependencyError, ProgramConfigurationError
from screener.models import Screen, HouseholdMember, ProgramEligibilitySnapshot, WhiteLabel, IncomeStream
from screener.views import eligibility_results, urgent_need_results


class BoomCalculator(ProgramCalculator):
    """Stands in for a calculator that crashes on data the gate let through — e.g. an
    income row whose frequency is unrecognized, so IncomeStream.yearly() falls through
    every branch and raises UnboundLocalError."""

    def household_eligible(self, e: Eligibility):
        raise UnboundLocalError("cannot access local variable 'yearly'")


class SkipCalculator(ProgramCalculator):
    """Stands in for the ordinary partial-screen path."""

    def calc(self) -> Eligibility:
        raise DependencyError()


class FineCalculator(ProgramCalculator):
    amount = 100


class MisconfiguredCalculator(ProgramCalculator):
    """Stands in for TxHcv/WaHcv with an unset `program.year` — our own data being wrong,
    which is a defect rather than a screen-data gap."""

    def household_eligible(self, e: Eligibility):
        raise ProgramConfigurationError("program year is not configured")


class OversizedHouseholdCalculator(ProgramCalculator):
    """Stands in for the seven HUD-backed calculators on a 9-person household: HUD's
    published tables stop at 8, so there is no income limit to test against."""

    amount = 100

    def household_eligible(self, e: Eligibility):
        hud_client.get_screen_il_ami(self.screen, "80%", "2025")


class MissingProgramsTestBase(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            county="Test County",
            household_size=1,
            household_assets=0,
            completed=False,
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
            student=False,
            pregnant=False,
            visually_impaired=False,
            disabled=False,
            long_term_disability=False,
        )

    def _seed_program(self, name_abbreviated: str) -> Program:
        """new_program() creates an inactive, uncategorized row; eligibility_results only
        looks at active + categorized + has_calculator programs."""
        if not hasattr(self, "_category"):
            self._category = ProgramCategory.objects.new_program_category(self.white_label.code, "test-category", None)

        program = Program.objects.new_program(self.white_label.code, name_abbreviated)
        program.active = True
        program.has_calculator = True
        program.category = self._category
        program.save()
        return program

    def _run(self):
        """Run eligibility_results inside a tracking context, as the results view does."""
        with track_external_api_failures():
            _programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)
        return missing_programs


class TestExternalApiFailureSetsMissingPrograms(MissingProgramsTestBase):
    def test_recorded_hud_failure_sets_missing_programs(self):
        """HUD-backed calculators catch HudIncomeClientError and degrade to "not eligible
        (income limit unknown)", so nothing raises and no program is skipped — the
        recorded failure is the only trace, and it has to flip the flag."""
        with track_external_api_failures():
            record_external_api_failure(HUD)
            _programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)

        self.assertTrue(missing_programs)

    def test_no_failure_leaves_flag_false(self):
        self.assertFalse(self._run())


class TestCalculatorCrashSetsMissingPrograms(MissingProgramsTestBase):
    def test_crash_is_reported_and_flagged_not_fatal(self):
        program = self._seed_program("boom")

        with patch.dict("programs.models.calculators", {"boom": BoomCalculator}, clear=False):
            with patch("screener.views.capture_exception") as mock_capture_exception:
                with patch("screener.views.capture_message") as mock_capture_message:
                    missing_programs = self._run()

        self.assertTrue(missing_programs)
        # Loud: both the exception and a human-readable context line, at error level.
        self.assertIsInstance(mock_capture_exception.call_args.args[0], UnboundLocalError)
        self.assertEqual(mock_capture_exception.call_args.kwargs["level"], "error")
        self.assertEqual(mock_capture_message.call_args.kwargs["level"], "error")

        # The message is static and the program rides in context + fingerprint: Sentry
        # should show one issue per broken program, not one per screen that hit it.
        message = mock_capture_message.call_args.args[0]
        self.assertNotIn(program.name_abbreviated, message)
        self.assertNotIn(str(self.screen.id), message)
        for mock in (mock_capture_exception, mock_capture_message):
            contexts = mock.call_args.kwargs["contexts"]
            self.assertEqual(contexts["program"]["name_abbreviated"], program.name_abbreviated)
            self.assertEqual(contexts["program"]["stage"], "eligibility")
            self.assertEqual(contexts["screen"]["id"], self.screen.id)
        self.assertEqual(
            mock_capture_message.call_args.kwargs["fingerprint"],
            ["program-eligibility-failure", program.name_abbreviated, "eligibility"],
        )
        # capture_exception keeps Sentry's own stack-trace grouping so two different bugs
        # in the same program stay separate issues.
        self.assertNotIn("fingerprint", mock_capture_exception.call_args.kwargs)

    def test_one_crashing_program_does_not_lose_the_others(self):
        """The whole point: previously this 500'd and the user got zero results."""
        self._seed_program("boom")
        self._seed_program("fine")

        with patch.dict(
            "programs.models.calculators",
            {"boom": BoomCalculator, "fine": FineCalculator},
            clear=False,
        ):
            with patch("screener.views.capture_exception"), patch("screener.views.capture_message"):
                with track_external_api_failures():
                    programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)

        self.assertTrue(missing_programs)
        returned = {p["short_name"] for p in programs}
        self.assertIn("fine", returned)
        self.assertNotIn("boom", returned)

    def test_dependency_error_stays_quiet(self):
        """An unanswered question is not a defect — flag the response, but don't page
        anyone."""
        self._seed_program("skip")

        with patch.dict("programs.models.calculators", {"skip": SkipCalculator}, clear=False):
            with patch("screener.views.capture_exception") as mock_capture_exception:
                with patch("screener.views.capture_message") as mock_capture_message:
                    missing_programs = self._run()

        self.assertTrue(missing_programs)
        mock_capture_exception.assert_not_called()
        mock_capture_message.assert_not_called()


class TestMalformedDataSetsMissingPrograms(MissingProgramsTestBase):
    def test_malformed_screen_data_is_reported_and_flagged(self):
        """Set independently of which calculators happen to declare the field: with no
        calculator declaring income_frequency, nothing would raise DependencyError, yet
        the run is still degraded."""
        IncomeStream.objects.create(
            screen=self.screen,
            household_member=self.head,
            type="wages",
            amount=100,
            frequency="fortnightly",
        )

        with patch("screener.views.capture_message") as mock_capture_message:
            missing_programs = self._run()

        self.assertTrue(missing_programs)
        kwargs = mock_capture_message.call_args.kwargs
        self.assertEqual(kwargs["level"], "error")

        # Static message; the screen id and the offending value are structured context, so
        # Sentry groups by the KIND of corruption (the field names) rather than by screen.
        message = mock_capture_message.call_args.args[0]
        self.assertNotIn("fortnightly", message)
        self.assertNotIn(str(self.screen.id), message)
        self.assertEqual(kwargs["contexts"]["malformed_data"]["fields"], ["income_frequency"])
        self.assertIn("fortnightly", kwargs["contexts"]["malformed_data"]["values"][0])
        self.assertEqual(kwargs["contexts"]["screen"]["id"], self.screen.id)
        self.assertEqual(kwargs["fingerprint"], ["malformed-screen-data", "income_frequency"])

    def test_same_corruption_on_two_screens_groups_together(self):
        """Two screens with the same defect must produce the same fingerprint — otherwise
        a widespread serializer drift arrives as thousands of separate Sentry issues."""
        fingerprints = []
        for _ in range(2):
            screen = Screen.objects.create(
                white_label=self.white_label,
                zipcode="78701",
                county="Test County",
                household_size=1,
                household_assets=0,
                completed=False,
            )
            member = HouseholdMember.objects.create(
                screen=screen,
                relationship="headOfHousehold",
                age=35,
                student=False,
                pregnant=False,
                visually_impaired=False,
                disabled=False,
                long_term_disability=False,
            )
            IncomeStream.objects.create(
                screen=screen, household_member=member, type="wages", amount=100, frequency="fortnightly"
            )
            with patch("screener.views.capture_message") as mock_capture_message:
                with track_external_api_failures():
                    eligibility_results(screen)
            fingerprints.append(mock_capture_message.call_args.kwargs["fingerprint"])

        self.assertEqual(fingerprints[0], fingerprints[1])

    def test_null_data_does_not_trigger_the_malformed_report(self):
        """A null income row is ordinary partial input: it still gates programs that
        declare it, but must not fire a Sentry error."""
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type=None, amount=None, frequency=None
        )

        with patch("screener.views.capture_message") as mock_capture_message:
            self._run()

        mock_capture_message.assert_not_called()


class TestPresentationCrashIsIsolated(MissingProgramsTestBase):
    """The eligibility call was guarded, but everything after it — warning calculators,
    translation lookups, snapshot construction — reads the same screen data and ran
    unguarded. A `fortnightly` income row crashing `calc_gross_income()` inside a warning
    calculator 500'd the response exactly as hard as one crashing the calculator itself.
    """

    def _attach_warning(self, program: Program, calculator: str) -> None:
        warning = WarningMessage.objects.new_warning(self.white_label.code, calculator)
        program.warning_messages.add(warning)

    def test_broken_warning_skips_only_that_program(self):
        """An unregistered warning calculator raises `... is not a valid calculator name`,
        which used to abort the entire response."""
        program = self._seed_program("fine")
        self._attach_warning(program, "no_such_warning_calculator")

        with patch.dict("programs.models.calculators", {"fine": FineCalculator}, clear=False):
            with patch("screener.views.capture_exception") as mock_capture_exception:
                with patch("screener.views.capture_message") as mock_capture_message:
                    with track_external_api_failures():
                        programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)

        self.assertTrue(missing_programs)
        self.assertNotIn("fine", {p["short_name"] for p in programs})
        mock_capture_exception.assert_called_once()
        self.assertEqual(
            mock_capture_message.call_args.kwargs["contexts"]["program"]["stage"],
            "presentation",
        )

    def test_a_broken_warning_does_not_lose_the_other_programs(self):
        broken = self._seed_program("broken")
        self._attach_warning(broken, "no_such_warning_calculator")
        self._seed_program("fine")

        with patch.dict(
            "programs.models.calculators",
            {"broken": FineCalculator, "fine": FineCalculator},
            clear=False,
        ):
            with patch("screener.views.capture_exception"), patch("screener.views.capture_message"):
                with track_external_api_failures():
                    programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)

        self.assertTrue(missing_programs)
        returned = {p["short_name"] for p in programs}
        self.assertIn("fine", returned)
        self.assertNotIn("broken", returned)

    def test_partial_output_is_rolled_back(self):
        """The crashed program must leave no half-rendered entry or snapshot row behind."""
        program = self._seed_program("broken")
        self._attach_warning(program, "no_such_warning_calculator")

        with patch.dict("programs.models.calculators", {"broken": FineCalculator}, clear=False):
            with patch("screener.views.capture_exception"), patch("screener.views.capture_message"):
                with track_external_api_failures():
                    programs, _missing, _categories, _pe_data = eligibility_results(self.screen)

        self.assertEqual(programs, [])
        self.assertFalse(ProgramEligibilitySnapshot.objects.filter(name_abbreviated=program.name_abbreviated).exists())


class TestUrgentNeedCrashIsIsolated(MissingProgramsTestBase):
    """urgent_need_results had no protection at all, and IlRentAsst calls the HUD client
    with no handler of its own — so a HUD outage took the whole results response down."""

    def setUp(self):
        super().setUp()
        self.screen.needs_food = True
        self.screen.save()

        category = UrgentNeedCategory.objects.create(name="food")
        need_type = UrgentNeedType.objects.new_urgent_need_type(self.white_label.code, "food-type", "")

        self.need = UrgentNeed.objects.new_urgent_need(self.white_label.code, "boom-need", "")
        self.need.active = True
        self.need.category_type = need_type
        self.need.save()
        self.need.type_short.add(category)
        self.need.functions.add(UrgentNeedFunction.objects.create(name="boom_need_function"))

    def test_crashing_urgent_need_is_reported_and_skipped(self):
        class BoomNeed(UrgentNeedFunctionCalculator):
            def eligible(self):
                raise UnboundLocalError("cannot access local variable 'yearly'")

        with patch.dict("screener.views.urgent_need_functions", {"boom_need_function": BoomNeed}, clear=False):
            with patch("screener.views.capture_exception") as mock_capture_exception:
                with patch("screener.views.capture_message") as mock_capture_message:
                    needs = urgent_need_results(self.screen, [])

        self.assertEqual(needs, [])
        mock_capture_exception.assert_called_once()
        self.assertEqual(
            mock_capture_message.call_args.kwargs["fingerprint"],
            ["urgent-need-failure", str(self.need.id)],
        )

    def test_dependency_error_in_an_urgent_need_stays_quiet(self):
        class SkipNeed(UrgentNeedFunctionCalculator):
            def eligible(self):
                raise DependencyError()

        with patch.dict("screener.views.urgent_need_functions", {"boom_need_function": SkipNeed}, clear=False):
            with patch("screener.views.capture_exception") as mock_capture_exception:
                with patch("screener.views.capture_message") as mock_capture_message:
                    needs = urgent_need_results(self.screen, [])

        self.assertEqual(needs, [])
        mock_capture_exception.assert_not_called()
        mock_capture_message.assert_not_called()


class TestMisconfiguredProgramIsLoud(MissingProgramsTestBase):
    """An unset `program.year` used to be raised as HudIncomeClientError, which the
    HUD-backed calculators caught and turned into a permanent, silent "not eligible
    (income limit unknown)". It is our own data being wrong, so it must be loud."""

    def test_configuration_error_is_reported_and_the_program_skipped(self):
        program = self._seed_program("misconfigured")

        with patch.dict("programs.models.calculators", {"misconfigured": MisconfiguredCalculator}, clear=False):
            with patch("screener.views.capture_exception") as mock_capture_exception:
                with patch("screener.views.capture_message") as mock_capture_message:
                    with track_external_api_failures():
                        programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)

        self.assertTrue(missing_programs)
        self.assertNotIn(program.name_abbreviated, {p["short_name"] for p in programs})
        self.assertIsInstance(mock_capture_exception.call_args.args[0], ProgramConfigurationError)
        self.assertEqual(mock_capture_message.call_args.kwargs["level"], "error")


class TestHouseholdOutsideHudTables(MissingProgramsTestBase):
    """HUD publishes income limits for households of 1-8. A 9-person household used to get
    a definite "not eligible (income limit unknown)" across all seven HUD-backed programs,
    with no flag and no event — a "No" derived from a number we never had."""

    def _make_oversized_household(self):
        self.screen.household_size = 9
        self.screen.save()

    def test_oversized_household_omits_the_program_and_flags_the_response(self):
        program = self._seed_program("oversized")
        self._make_oversized_household()

        with patch.dict("programs.models.calculators", {"oversized": OversizedHouseholdCalculator}, clear=False):
            with patch("screener.views.capture_exception") as mock_capture_exception:
                with patch("screener.views.capture_message") as mock_capture_message:
                    with track_external_api_failures():
                        programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)

        # Omitted rather than answered "not eligible".
        self.assertNotIn(program.name_abbreviated, {p["short_name"] for p in programs})
        self.assertTrue(missing_programs)
        # Quiet: nothing external failed, so this must not page anyone or tell the user an
        # external service is down.
        mock_capture_exception.assert_not_called()
        mock_capture_message.assert_not_called()

    def test_oversized_household_does_not_claim_an_external_api_failed(self):
        self._seed_program("oversized")
        self._make_oversized_household()

        with patch.dict("programs.models.calculators", {"oversized": OversizedHouseholdCalculator}, clear=False):
            with track_external_api_failures() as _:
                eligibility_results(self.screen)
                from integrations.external_api_status import get_external_api_failures

                self.assertEqual(get_external_api_failures(), [])

    def test_supported_household_size_still_reaches_hud(self):
        """The gate must be the household size, not the program: an 8-person household is
        inside HUD's tables and must still be calculated."""
        self._seed_program("oversized")
        self.screen.household_size = 8
        self.screen.save()

        with patch.dict("programs.models.calculators", {"oversized": OversizedHouseholdCalculator}, clear=False):
            with patch.object(hud_client, "get_screen_il_ami", return_value=50_000) as mock_lookup:
                with track_external_api_failures():
                    programs, missing_programs, _categories, _pe_data = eligibility_results(self.screen)

        mock_lookup.assert_called_once()
        self.assertIn("oversized", {p["short_name"] for p in programs})
        self.assertFalse(missing_programs)
