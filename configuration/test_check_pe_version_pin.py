"""Tests for the check_pe_version_pin guard (MFB-1319)."""

from io import StringIO
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from configuration.models import PolicyEngineConfig
from integrations.clients.policyengine import versions

SERVED = {"current": "1.732.0", "frontier": "1.744.0"}


def run_check():
    out, err = StringIO(), StringIO()
    call_command("check_pe_version_pin", stdout=out, stderr=err)
    return out.getvalue() + err.getvalue()


class TestCheckPEVersionPin(TestCase):
    def setUp(self):
        cache.delete(versions._PE_VERSIONS_CACHE_KEY)

    def _pe_returns(self, payload):
        return patch.object(versions.requests, "get", return_value=_Response(payload))

    def _pin(self, version):
        PolicyEngineConfig.objects.create(policyengine_version=version)

    def test_pin_equal_to_current_passes(self):
        self._pin("1.732.0")
        with self._pe_returns(SERVED):
            self.assertIn("matches PE current: OK", run_check())

    def test_pin_equal_to_frontier_passes_with_a_warning(self):
        self._pin("1.744.0")
        with self._pe_returns(SERVED):
            output = run_check()
        self.assertIn("is PE frontier, not current (1.732.0)", output)

    def test_pin_below_current_fails(self):
        self._pin("1.715.2")
        with self._pe_returns(SERVED):
            with self.assertRaisesRegex(CommandError, "not served by PolicyEngine"):
                run_check()

    def test_pin_above_frontier_fails(self):
        # PE serves only current and frontier, so a newer pin is as unservable as an older one.
        self._pin("1.750.0")
        with self._pe_returns(SERVED):
            with self.assertRaisesRegex(CommandError, "not served by PolicyEngine"):
                run_check()

    def test_pin_between_current_and_frontier_fails(self):
        self._pin("1.740.0")
        with self._pe_returns(SERVED):
            with self.assertRaises(CommandError):
                run_check()

    def test_empty_pin_passes_without_calling_pe(self):
        with patch.object(versions.requests, "get") as get:
            self.assertIn("unpinned", run_check())
        get.assert_not_called()

    def test_endpoint_unreachable_passes(self):
        self._pin("1.715.2")
        with patch.object(versions.requests, "get", side_effect=requests.ConnectionError("down")):
            self.assertIn("skipping", run_check())

    def test_non_string_current_warns_and_passes(self):
        self._pin("1.715.2")
        with self._pe_returns({"current": 123, "frontier": "1.744.0"}):
            self.assertIn("Unexpected PolicyEngine /versions/us payload", run_check())

    def test_missing_current_is_treated_as_unreachable(self):
        # _fetch_pe_versions rejects a payload without `current`, so the command skips.
        self._pin("1.715.2")
        with self._pe_returns({"frontier": "1.744.0"}):
            self.assertIn("skipping", run_check())

    def test_ignores_stale_cache(self):
        # The cache still says 1.700.0 is current, which would let this pin pass.
        self._pin("1.700.0")
        cache.set(versions._PE_VERSIONS_CACHE_KEY, {"current": "1.700.0", "frontier": "1.700.0"}, 3600)
        with self._pe_returns(SERVED):
            with self.assertRaises(CommandError):
                run_check()


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload
