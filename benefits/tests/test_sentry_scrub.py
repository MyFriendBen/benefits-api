"""Tests for the Sentry before_send hook that keeps addresses and upstream keys out of events."""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from typing import Any
from unittest.mock import patch
from wsgiref.util import setup_testing_defaults

import sentry_sdk
from django.core.wsgi import get_wsgi_application
from django.test import TestCase, override_settings
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.transport import Transport

from benefits.sentry_scrub import scrub_event
from benefits.tests.cache_override import LOCAL_CACHE
from integrations.clients.google_places import GooglePlacesClient
from integrations.clients.rewiring_america import RewiringAmericaClient

FAKE_ADDRESS = "742 Invented Lane, Nowhere, CO 80000"
FAKE_KEY = "fake-places-key-for-tests"


class ScrubEventTest(TestCase):
    def test_drops_query_string_on_every_event(self) -> None:
        event = {"request": {"url": "https://api.example/api/screens/", "query_string": "a=1"}}
        scrubbed = scrub_event(event, {})
        self.assertNotIn("query_string", scrubbed["request"])

    def test_strips_query_from_request_url(self) -> None:
        event = {"request": {"url": "https://api.example/api/screens/?a=1"}}
        self.assertEqual(scrub_event(event, {})["request"]["url"], "https://api.example/api/screens/")

    def test_keeps_body_and_frame_vars_outside_address_endpoints(self) -> None:
        frame = {"function": "f", "vars": {"x": "1"}}
        event = {
            "request": {"url": "https://api.example/api/screens/", "data": {"zipcode": "80000"}},
            "exception": {"values": [{"stacktrace": {"frames": [frame]}}]},
        }
        scrubbed = scrub_event(event, {})
        self.assertIn("data", scrubbed["request"])
        self.assertIn("vars", frame)

    def test_drops_body_and_frame_vars_on_address_endpoints(self) -> None:
        for url in (
            "https://api.example/api/places/autocomplete/",
            "https://api.example/api/screener-options/cesn/rem-impact/",
        ):
            frame = {"function": "f", "vars": {"address": FAKE_ADDRESS}}
            event = {
                "request": {"url": url, "data": {"address": FAKE_ADDRESS}},
                "exception": {"values": [{"stacktrace": {"frames": [frame]}}]},
            }
            scrubbed = scrub_event(event, {})
            self.assertNotIn("data", scrubbed["request"], url)
            self.assertNotIn("vars", frame, url)

    def test_strips_query_from_httplib_breadcrumbs(self) -> None:
        crumb = {
            "category": "httplib",
            "data": {"url": "https://maps.example/json?key=k", "http.query": f"input=x&key={FAKE_KEY}"},
        }
        other = {"category": "query", "data": {"http.query": "kept"}}
        event = {"breadcrumbs": {"values": [crumb, other]}}
        scrub_event(event, {})
        self.assertNotIn("http.query", crumb["data"])
        self.assertEqual(crumb["data"]["url"], "https://maps.example/json")
        self.assertEqual(other["data"]["http.query"], "kept")


class _RecordingTransport(Transport):
    events: list[dict[str, Any]] = []

    def capture_envelope(self, envelope: Any) -> None:
        for item in envelope.items:
            if item.headers.get("type") == "event" and item.payload.json:
                self.events.append(item.payload.json)


class _MalformedUpstream(BaseHTTPRequestHandler):
    """200 with a body the clients don't expect, so the views raise an unhandled exception."""

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "OK", "predictions": [{"unexpected": 1}]}).encode())

    def log_message(self, *_args: Any) -> None:
        pass


@contextmanager
def _recording_sentry() -> Iterator[list[dict[str, Any]]]:
    global_scope = sentry_sdk.Scope.get_global_scope()
    previous = global_scope.client
    _RecordingTransport.events = []
    sentry_sdk.init(
        dsn="https://public@example.invalid/1",
        integrations=[DjangoIntegration()],
        transport=_RecordingTransport,
        before_send=scrub_event,
    )
    try:
        yield _RecordingTransport.events
    finally:
        sentry_sdk.flush()
        global_scope.set_client(previous)


@override_settings(CACHES=LOCAL_CACHE, GOOGLE_MAPS_API_KEY=FAKE_KEY, ALLOWED_HOSTS=["*"])
class AddressEndpointEventTest(TestCase):
    """An unhandled exception on an address endpoint yields an event with no address and no key.

    Goes through the WSGI app rather than the test client, because Sentry's WSGI middleware
    is what attaches the request URL and query string in production.
    """

    def setUp(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _MalformedUpstream)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        upstream = f"http://127.0.0.1:{server.server_port}"
        for target in (
            patch.object(GooglePlacesClient, "BASE_URL", upstream),
            patch.object(RewiringAmericaClient, "BASE_URL", upstream),
            patch("screener.views.PlacesRateThrottle.allow_request", return_value=True),
            patch("screener.views.RemRateThrottle.allow_request", return_value=True),
        ):
            target.start()
            self.addCleanup(target.stop)

    def _wsgi(self, method: str, path: str, query: str = "", body: dict[str, str] | None = None) -> str:
        raw = json.dumps(body).encode() if body is not None else b""
        environ: dict[str, Any] = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(raw)),
            "wsgi.input": BytesIO(raw),
        }
        setup_testing_defaults(environ)
        statuses: list[str] = []
        b"".join(get_wsgi_application()(environ, lambda s, _h, *_a: statuses.append(s)))
        return statuses[0]

    def _assert_clean(self, events: list[dict[str, Any]]) -> None:
        self.assertTrue(events, "expected the unhandled exception to reach Sentry")
        blob = json.dumps(events)
        for leaked in ("Invented", "742", FAKE_KEY):
            self.assertNotIn(leaked, blob)

    def test_places_get(self) -> None:
        with _recording_sentry() as events:
            status = self._wsgi("GET", "/api/places/autocomplete/", f"input={FAKE_ADDRESS.replace(' ', '+')}")
        self.assertTrue(status.startswith("500"), status)
        self._assert_clean(events)

    def test_places_post(self) -> None:
        with _recording_sentry() as events:
            status = self._wsgi("POST", "/api/places/autocomplete/", body={"input": FAKE_ADDRESS})
        self.assertTrue(status.startswith("500"), status)
        self._assert_clean(events)

    @patch("screener.views.RemImpactSerializer", side_effect=KeyError("fuel_results"))
    def test_rem_impact_post(self, _serializer: Any) -> None:
        body = {"upgrade": "hvac__heat_pump", "address": FAKE_ADDRESS, "heating_fuel": "natural_gas"}
        with _recording_sentry() as events:
            status = self._wsgi("POST", "/api/screener-options/cesn/rem-impact/", body=body)
        self.assertTrue(status.startswith("500"), status)
        self._assert_clean(events)
