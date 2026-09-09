"""A degraded run is identifiable after the fact.

`had_error` is a crash marker: True at creation, flipped False once the run finishes. A run
that finished but lost its PolicyEngine programs to a failed request finishes, so it used to
be persisted as an ordinary snapshot — indistinguishable, in any later query, from one where
nothing went wrong. `had_external_api_failure` records that difference.
"""

from unittest.mock import patch

from django.test import TestCase

from integrations.external_api_status import POLICY_ENGINE, record_external_api_failure, track_external_api_failures
from screener.models import EligibilitySnapshot, HouseholdMember, Screen, WhiteLabel
from screener.views import eligibility_results


class TestSnapshotDegradedFlag(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            completed=False,
            agree_to_tos=True,
            household_size=1,
        )
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=35)

    def _run(self, pe_fails: bool):
        empty = {"eligibility": {}, "_pe_data": {"request": None, "response": None}}

        def fake_calc(*args, **kwargs):
            if pe_fails:
                record_external_api_failure(POLICY_ENGINE)
            return empty

        with patch("screener.views.calc_pe_eligibility", side_effect=fake_calc), track_external_api_failures():
            eligibility_results(self.screen, False)

        return EligibilitySnapshot.objects.filter(screen=self.screen).latest("submission_date")

    def test_clean_run_is_not_flagged(self):
        snapshot = self._run(pe_fails=False)

        self.assertFalse(snapshot.had_error)
        self.assertFalse(snapshot.had_external_api_failure)

    def test_degraded_run_is_flagged_but_still_counts_as_finished(self):
        snapshot = self._run(pe_fails=True)

        self.assertTrue(snapshot.had_external_api_failure)
        # Still had_error=False: the run finished and the user got a results page. The
        # `had_error=False` filters that pick the latest usable snapshot (assistant context,
        # NPS, the previous-results diff) must keep seeing it.
        self.assertFalse(snapshot.had_error)
