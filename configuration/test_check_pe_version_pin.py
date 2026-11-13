"""Tests for the check_pe_version_pin guard (MFB-1319)."""

from io import StringIO
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from configuration.models import PolicyEngineConfig
from integrations.clients.policyengine import versions


def run_check(pe_current="1.732.0"):
    out, err = StringIO(), StringIO()
    call_command("check_pe_version_pin", stdout=out, stderr=err)
    return out.getvalue() + err.getvalue()


class TestCheckPEVersionPin(TestCase):
    def setUp(self):
        cache.delete(versions._PE_VERSIONS_CACHE_KEY)

    def _pe_returns(self, payload):
        return patch.object(versions.requests, "get", return_value=_Response(payload))

    def test_pin_below_current_fails(self):
        PolicyEngineConfig.objects.create(policyengine_version="1.715.2")
        with self._pe_returns({"current": "1.732.0", "frontier": "1.744.0"}):
            with self.assertRaises(SystemExit) as ctx:
                run_check()
        self.assertEqual(ctx.exception.code, 1)

    def test_pin_equal_to_current_passes(self):
        PolicyEngineConfig.objects.create(policyengine_version="1.732.0")
        with self._pe_returns({"current": "1.732.0", "frontier": "1.744.0"}):
            self.assertIn("OK", run_check())

    def test_pin_above_current_passes(self):
        PolicyEngineConfig.objects.create(policyengine_version="1.744.0")
        with self._pe_returns({"current": "1.732.0", "frontier": "1.744.0"}):
            self.assertIn("OK", run_check())

    def test_numeric_not_lexical_comparison(self):
        # "1.9.0" > "1.10.0" as strings; the tuple comparison must get this right.
        PolicyEngineConfig.objects.create(policyengine_version="1.9.0")
        with self._pe_returns({"current": "1.10.0", "frontier": "1.10.0"}):
            with self.assertRaises(SystemExit):
                run_check()

    def test_empty_pin_passes_without_calling_pe(self):
        with patch.object(versions.requests, "get") as get:
            self.assertIn("unpinned", run_check())
        get.assert_not_called()

    def test_endpoint_unreachable_passes(self):
        PolicyEngineConfig.objects.create(policyengine_version="1.715.2")
        with patch.object(versions.requests, "get", side_effect=requests.ConnectionError("down")):
            self.assertIn("skipping", run_check())

    def test_ignores_stale_cache(self):
        PolicyEngineConfig.objects.create(policyengine_version="1.715.2")
        cache.set(versions._PE_VERSIONS_CACHE_KEY, {"current": "1.700.0"}, 3600)
        with self._pe_returns({"current": "1.732.0", "frontier": "1.744.0"}):
            with self.assertRaises(SystemExit):
                run_check()


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload
