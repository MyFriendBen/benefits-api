"""Harness test for the PolicyEngine integration-test helpers.

This validates the record/replay machinery itself — explicit primary keys, the pinned
version, the replay token stub, and the body matcher in conftest — using one household as its
subject. A program's own PolicyEngine tests live next to the program
(``programs/programs/{state}/{program}/tests/``), not here.

If this test fails to replay, the harness is broken; see docs/TESTING.md.

One caveat when it *does* fail: the subject is a real calculator, ``TxHeadStart``, which
inherits its inputs from the federal ``HeadStart``. Adding an input there changes the request
body and so breaks this test with a body mismatch — that is a signal about the calculator
change, not about the harness. Re-record after reviewing the new body.
"""

import unittest
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from benefits.tests.cache_override import LOCAL_CACHE
from integrations.clients.policyengine import engines
from integrations.clients.policyengine.engines import _PE_TOKEN_CACHE_KEY
from programs.programs.testing_fixtures.pe_integration import (
    PE_TEST_VERSION,
    TEST_PE_TOKEN,
    PeIntegrationTestCase,
    check_pe_version_pin,
    check_program_vintage,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
    stub_pe_token_for_replay,
)
from programs.programs.cross_white_label.head_start.tx import TxHeadStart

PE_VERSION = "1.786.5"
PE_VERSION_REASON = (
    "Recorded before the suite-wide pin. Remove PE_VERSION and this reason once the module is "
    "re-recorded at PE_TEST_VERSION."
)


@pytest.mark.integration
class TestPeIntegrationHarness(PeIntegrationTestCase):
    # The asserted value has held across 1.779.3 → 1.784.3 → 1.786.5.
    pe_version = PE_VERSION
    pe_version_reason = PE_VERSION_REASON

    def test_replays_a_member_level_program_from_a_cassette(self):
        """One household, one POST, one cassette: a 3-year-old under the income limit.

        Member-level on purpose — the response is keyed by household member id, so this is
        what proves the explicit-pk rule actually makes a cassette replayable.
        """
        screen = make_screen(
            screen_id=1,
            white_label_code="tx",
            state_code="TX",
            household_size=2,
            zipcode="78701",
            county="Travis County",
        )
        parent = add_member(screen, member_id=1, relationship="headOfHousehold", age=34)
        add_income(parent, amount=1_496)
        add_member(screen, member_id=2, relationship="child", age=3)

        program = make_program("tx", "tx_head_start", year="2025")

        eligibility = calc_pe_program(screen, TxHeadStart, program)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), 12_076)


class TestCheckPeVersionPin(SimpleTestCase):
    """A module may sit behind the suite pin, but only with a stated reason."""

    def test_the_suite_pin_needs_no_reason(self) -> None:
        check_pe_version_pin("TestSomething", PE_TEST_VERSION, "")

    def test_an_override_with_a_reason_passes(self) -> None:
        check_pe_version_pin("TestSomething", "1.0.0", "recorded before the suite-wide pin")

    def test_an_override_without_a_reason_fails(self) -> None:
        with self.assertRaisesMessage(AssertionError, "Set pe_version_reason"):
            check_pe_version_pin("TestSomething", "1.0.0", "  ")

    def test_an_empty_pin_fails(self) -> None:
        with self.assertRaisesMessage(AssertionError, "must set pe_version"):
            check_pe_version_pin("TestSomething", "", "")

    def test_the_default_pin_is_the_suite_pin(self) -> None:
        self.assertEqual(PeIntegrationTestCase.pe_version, PE_TEST_VERSION)


class TestCheckProgramVintage(TestCase):
    """A scenario runs at the edition programs/vintage.py records, unless it says why not."""

    def test_the_recorded_edition_passes(self) -> None:
        check_program_vintage(make_program("mo", "mo_pts", year="2025", state_code="MO"))

    def test_another_year_fails(self) -> None:
        program = make_program("mo", "mo_pts", year="2026", state_code="MO")

        with self.assertRaisesMessage(AssertionError, "programs/vintage.py records 2025"):
            check_program_vintage(program)

    def test_another_year_with_a_reason_passes(self) -> None:
        check_program_vintage(make_program("mo", "mo_pts", year="2026", state_code="MO"), "year-parameter guard")

    def test_a_program_with_no_recorded_vintage_is_not_checked(self) -> None:
        check_program_vintage(make_program("mo", "not_in_vintage", year="2025", state_code="MO"))


# A per-process cache, as in test_token_cache_survives_test_flush.py: the token key is the one a
# developer's real token lives under, and clear_cache carries it across tests, so a token written
# to the ambient Redis here would replace theirs and could later be sent live by a recording run.
@override_settings(CACHES=LOCAL_CACHE)
class TestStubPeTokenForReplay(SimpleTestCase):
    """Replay never authenticates and never writes the token cache; recording uses a real token."""

    def setUp(self) -> None:
        super().setUp()
        self.real_fetch = engines._fetch_pe_bearer_token
        cache.delete(_PE_TOKEN_CACHE_KEY)

    def _stub(self, recording: bool, test: unittest.TestCase) -> None:
        with mock.patch("programs.programs.testing_fixtures.pe_integration._can_record", return_value=recording):
            stub_pe_token_for_replay(test)

    def test_replay_gets_the_placeholder_without_caching_it(self) -> None:
        self._stub(recording=False, test=self)

        self.assertEqual(engines._fetch_pe_bearer_token(), TEST_PE_TOKEN)
        self.assertIsNone(cache.get(_PE_TOKEN_CACHE_KEY))

    def test_replay_leaves_a_cached_real_token_alone(self) -> None:
        cache.set(_PE_TOKEN_CACHE_KEY, "real-token", timeout=600)

        self._stub(recording=False, test=self)

        self.assertEqual(engines._fetch_pe_bearer_token(), TEST_PE_TOKEN)
        self.assertEqual(cache.get(_PE_TOKEN_CACHE_KEY), "real-token")

    def test_the_replay_stub_ends_with_the_test(self) -> None:
        test = unittest.TestCase()
        self._stub(recording=False, test=test)

        test.doCleanups()

        self.assertIs(engines._fetch_pe_bearer_token, self.real_fetch)

    def test_recording_fetches_for_real(self) -> None:
        self._stub(recording=True, test=self)

        self.assertIs(engines._fetch_pe_bearer_token, self.real_fetch)

    def test_recording_drops_a_leftover_placeholder(self) -> None:
        cache.set(_PE_TOKEN_CACHE_KEY, TEST_PE_TOKEN, timeout=None)

        self._stub(recording=True, test=self)

        self.assertIsNone(cache.get(_PE_TOKEN_CACHE_KEY))

    def test_recording_keeps_a_cached_real_token(self) -> None:
        cache.set(_PE_TOKEN_CACHE_KEY, "real-token", timeout=600)

        self._stub(recording=True, test=self)

        self.assertEqual(cache.get(_PE_TOKEN_CACHE_KEY), "real-token")
