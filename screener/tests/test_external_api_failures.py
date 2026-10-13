"""`external_api_failures` reaches the results response, which is what raises the banner.

The results page shows "You may be eligible for more programs than those listed" whenever
the list is non-empty. Integrations record into it, and `all_results` reads it back into the
response. These run the real view path, so a failure recorded deep in a calculator or the
PolicyEngine client has to survive the trip to the payload the frontend reads.

Nurturing Futures stands in for every HUD-backed calculator: it is the one that records a
HUD failure today.
"""

from datetime import date
from unittest.mock import patch

from django.test import TestCase

from integrations.clients.hud_income_limits import HudIncomeClientError
from integrations.external_api_status import HUD, POLICY_ENGINE, record_external_api_failure
from programs.models import FederalPoveryLimit, Program, ProgramCategory
from programs.programs.testing_fixtures.households import add_member, make_screen
from screener.models import Screen
from screener.tests.helpers import seed_program
from screener.views import all_results

NF_HUD_LOOKUP = "programs.programs.white_labels.co.nf.calculator.hud_client.get_screen_mtsp_ami"
NO_PE_RESULTS = {"eligibility": {}, "_pe_data": {}}


class TestExternalApiFailuresInResponse(TestCase):
    def setUp(self):
        self.screen = make_screen(
            white_label_code="co", state_code="CO", household_size=2, zipcode="80301", county="Boulder County"
        )
        add_member(self.screen, age=30, yearly_income=20_000, stored_age=False)
        add_member(self.screen, relationship="child", age=None, birth_year_month=date(2024, 5, 1), stored_age=False)

        seed_program(self.screen.white_label, "co_nf")
        program = Program.objects.get(white_label=self.screen.white_label, name_abbreviated="co_nf")
        program.active = True
        program.has_calculator = True
        program.category = ProgramCategory.objects.new_program_category(white_label="co", external_name="cash", icon="")
        program.year, _ = FederalPoveryLimit.objects.get_or_create(year="2026", defaults={"period": "2026"})
        program.save()

    def results(self, hud_limit=None, hud_error=None, pe_fails=False) -> dict:
        def fake_pe(*_args, **_kwargs) -> dict:
            if pe_fails:
                record_external_api_failure(POLICY_ENGINE)
            return NO_PE_RESULTS

        with patch(NF_HUD_LOOKUP, return_value=hud_limit, side_effect=hud_error), patch(
            "screener.views.calc_pe_eligibility", side_effect=fake_pe
        ):
            return all_results(Screen.objects.get(pk=self.screen.pk))

    def nf_eligible(self, results: dict) -> bool:
        return next(p for p in results["programs"] if p["name_abbreviated"] == "co_nf")["eligible"]

    def test_hud_down_is_reported(self):
        results = self.results(hud_error=HudIncomeClientError("HUD unavailable"))

        self.assertEqual(results["external_api_failures"], [HUD])
        self.assertFalse(self.nf_eligible(results))

    def test_hud_answering_reports_nothing(self):
        results = self.results(hud_limit=36_000)

        self.assertEqual(results["external_api_failures"], [])
        self.assertTrue(self.nf_eligible(results))

    def test_policy_engine_down_is_reported(self):
        results = self.results(hud_limit=36_000, pe_fails=True)

        self.assertEqual(results["external_api_failures"], [POLICY_ENGINE])

    def test_both_down_are_reported_together(self):
        results = self.results(hud_error=HudIncomeClientError("HUD unavailable"), pe_fails=True)

        self.assertEqual(results["external_api_failures"], sorted([HUD, POLICY_ENGINE]))

    def test_failures_do_not_leak_into_the_next_request(self):
        self.results(hud_error=HudIncomeClientError("HUD unavailable"), pe_fails=True)

        self.assertEqual(self.results(hud_limit=36_000)["external_api_failures"], [])
