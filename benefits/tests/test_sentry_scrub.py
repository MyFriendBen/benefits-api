"""Tests for the Sentry before_send hook that keeps addresses, phone numbers and upstream keys out of events."""

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

from django.contrib.auth.models import Permission
from django.core.signals import request_finished, request_started
from django.db import close_old_connections
from rest_framework.authtoken.models import Token

from authentication.models import User
from benefits.sentry_scrub import SENTRY_PRIVACY_OPTIONS, scrub_event
from benefits.tests.cache_override import LOCAL_CACHE
from screener.models import Screen, WhiteLabel
from screener.throttles import RateWindow
from integrations.clients.google_places import GooglePlacesClient
from integrations.clients.rewiring_america import RewiringAmericaClient

FAKE_ADDRESS = "742 Invented Lane, Nowhere, CO 80000"
FAKE_KEY = "fake-places-key-for-tests"
# A stray query string on a POST still reaches Sentry's WSGI middleware, so the scrubber must drop it.
ADDRESS_QUERY = f"address={FAKE_ADDRESS.replace(' ', '+')}"


PLACES_URL = "https://api.example/api/places/autocomplete/"
REM_URL = "https://api.example/api/screener-options/cesn/rem-impact/"
MESSAGES_URL = "https://api.example/api/messages/"
FAKE_PHONE = "+13035550142"
FAKE_NAME = "Invented Person"
FAKE_EMAIL = "invented.person@example.com"


def _event(url: str) -> dict[str, Any]:
    return {
        "request": {
            "url": url,
            "query_string": ADDRESS_QUERY,
            "data": {"address": FAKE_ADDRESS},
        },
        "exception": {"values": [{"stacktrace": {"frames": [{"function": "f", "vars": {"address": FAKE_ADDRESS}}]}}]},
        "threads": {"values": [{"stacktrace": {"frames": [{"function": "f", "vars": {"address": FAKE_ADDRESS}}]}}]},
        "breadcrumbs": {
            "values": [
                {
                    "category": "httplib",
                    "data": {
                        "url": f"https://maps.example/json?input=742+Invented&key={FAKE_KEY}",
                        "http.query": f"input=742+Invented&key={FAKE_KEY}",
                        "http.fragment": "",
                    },
                },
                {"category": "query", "data": {"http.query": "kept"}},
            ]
        },
    }


class ScrubEventTest(TestCase):
    def test_drops_everything_that_can_carry_an_address_on_address_endpoints(self) -> None:
        for url in (PLACES_URL, REM_URL, PLACES_URL.rstrip("/"), f"{REM_URL}?address=742+Invented"):
            scrubbed = scrub_event(_event(url), {})
            request = scrubbed["request"]
            self.assertEqual(request["url"], url.split("?")[0], url)
            self.assertNotIn("query_string", request, url)
            self.assertNotIn("data", request, url)
            for key in ("exception", "threads"):
                self.assertNotIn("vars", scrubbed[key]["values"][0]["stacktrace"]["frames"][0], url)
            httplib, other = scrubbed["breadcrumbs"]["values"]
            self.assertEqual(httplib["data"], {"url": "https://maps.example/json"}, url)
            self.assertEqual(other["data"], {"http.query": "kept"}, url)

    def test_drops_the_body_and_locals_on_the_message_endpoint(self) -> None:
        for url in (MESSAGES_URL, MESSAGES_URL.rstrip("/")):
            event = _event(url)
            event["request"]["data"] = {"screen": "s", "phone": FAKE_PHONE}
            event["exception"]["values"][0]["stacktrace"]["frames"][0]["vars"] = {"phone": FAKE_PHONE}

            scrubbed = scrub_event(event, {})

            self.assertNotIn("data", scrubbed["request"], url)
            self.assertNotIn("vars", scrubbed["exception"]["values"][0]["stacktrace"]["frames"][0], url)
            self.assertNotIn("3035550142", json.dumps(scrubbed), url)

    def test_redacts_contacts_from_exception_text_on_the_message_endpoint(self) -> None:
        event = _event(MESSAGES_URL)
        event["exception"]["values"][0][
            "value"
        ] = "HTTP 400 error: The 'To' number +1 (303) 555-0142 is not valid (21211); bounced a.person@example.com"

        value = scrub_event(event, {})["exception"]["values"][0]["value"]

        self.assertEqual(value, "HTTP 400 error: The 'To' number [contact] is not valid (21211); bounced [contact]")

    def test_leaves_other_endpoints_alone_apart_from_the_body(self) -> None:
        # The address and contact scrubbing is for those endpoints only. The request body is
        # dropped everywhere (MFB-2554), and is the one thing that changes on any other.
        for url in (
            "https://api.example/api/eligibility/1",
            "https://api.example/api/messages/extra/",
            "https://api.example/api/places/autocomplete/extra/",
            "https://api.example/api/screener-options/cesn/referrers/",
        ):
            event = _event(url)
            expected = json.loads(json.dumps(event))
            del expected["request"]["data"]
            self.assertEqual(scrub_event(event, {}), expected, url)

    def test_celery_job_extra_loses_args_and_kwargs(self) -> None:
        event = {
            "extra": {
                "celery-job": {"task_name": "screener.benji_sms_turn", "args": ["c", "+13035550100"], "kwargs": {}}
            },
            "exception": {
                "values": [{"stacktrace": {"frames": [{"function": "turn", "vars": {"to": "+13035550100"}}]}}]
            },
        }
        scrubbed = scrub_event(event, {})
        self.assertEqual(scrubbed["extra"]["celery-job"], {"task_name": "screener.benji_sms_turn"})
        self.assertNotIn("vars", scrubbed["exception"]["values"][0]["stacktrace"]["frames"][0])

    def test_frame_vars_go_on_any_celery_tagged_event(self) -> None:
        """Tagged by Celery's integration but with no celery-job extra: the tag alone counts."""
        for tags in ({"celery_task_id": "t-1"}, [["celery_task_id", "t-1"]], [("celery_task_id", "t-1")]):
            event = {
                "tags": tags,
                "exception": {"values": [{"stacktrace": {"frames": [{"function": "turn", "vars": {"to": "+1303"}}]}}]},
            }
            scrubbed = scrub_event(event, {})
            self.assertNotIn("vars", scrubbed["exception"]["values"][0]["stacktrace"]["frames"][0], tags)

    def test_frame_vars_stay_on_other_events(self) -> None:
        event = {
            "tags": {"other": "x"},
            "exception": {"values": [{"stacktrace": {"frames": [{"function": "view", "vars": {"x": 1}}]}}]},
        }
        self.assertEqual(scrub_event(event, {})["exception"]["values"][0]["stacktrace"]["frames"][0]["vars"], {"x": 1})

    def test_message_sids_are_redacted_wherever_they_appear(self) -> None:
        sid, mms = "SM" + "ab" * 16, "MM" + "0" * 32
        event = {
            "message": f"failed for {sid}",
            "exception": {"values": [{"value": f"GET /2010-04-01/Accounts/AC1/Messages/{sid}.json: 404"}]},
            "breadcrumbs": {
                "values": [
                    {"category": "celery.worker.strategy", "data": {"args": f"('c', '{sid}')"}},
                    {"category": "httplib", "data": {"url": f"https://api.twilio.com/Messages/{mms}/Media.json"}},
                ]
            },
            "extra": {"nested": [{"tuple": (sid,)}]},
        }
        scrubbed = json.dumps(scrub_event(event, {}))
        self.assertNotIn(sid, scrubbed)
        self.assertNotIn(mms, scrubbed)
        self.assertIn("[MessageSid]", scrubbed)

    def test_strings_that_only_look_alike_are_left_alone(self) -> None:
        event = {"message": "SMS sent; SM123; " + "SM" + "AB" * 16 + "; CA" + "0" * 32}
        self.assertEqual(scrub_event(event, {}), event)

    def test_drops_the_request_body_on_every_endpoint(self) -> None:
        # MFB-2554: not only the address and contact endpoints. The sign-up and screen
        # endpoints carry names, emails and household details.
        screen = "11111111-2222-3333-4444-555555555555"
        for url in (
            f"https://api.example/api/users/{screen}/",
            "https://api.example/api/screens/",
            f"https://api.example/api/screens/{screen}/current-benefits/",
            "https://api.example/api/eligibility/" + screen,
            PLACES_URL,
            MESSAGES_URL,
        ):
            with self.subTest(url=url):
                event = {
                    "request": {"url": url, "method": "PUT", "data": {"first_name": FAKE_NAME, "email": FAKE_EMAIL}}
                }
                scrubbed = scrub_event(event, {})
                self.assertNotIn("data", scrubbed["request"])
                self.assertNotIn(FAKE_EMAIL, json.dumps(scrubbed))

    def test_keeps_the_rest_of_the_request_on_other_endpoints(self) -> None:
        # Only the body goes. The URL, method and headers are what make an event debuggable.
        event = {
            "request": {
                "url": "https://api.example/api/screens/",
                "method": "POST",
                "query_string": "a=1",
                "headers": {"Content-Type": "application/json"},
                "data": {"household_size": 3},
            }
        }
        request = scrub_event(event, {})["request"]
        self.assertEqual(request["url"], "https://api.example/api/screens/")
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["query_string"], "a=1")
        self.assertEqual(request["headers"], {"Content-Type": "application/json"})
        self.assertNotIn("data", request)

    def test_a_body_that_is_already_a_placeholder_is_dropped_too(self) -> None:
        # With max_request_body_size "never" the SDK leaves an empty value behind rather than no key.
        event = {"request": {"url": "https://api.example/api/screens/", "data": ""}}
        self.assertNotIn("data", scrub_event(event, {})["request"])

    def test_event_without_request_is_unchanged(self) -> None:
        event = {"message": "background job failed"}
        self.assertEqual(scrub_event(event, {}), {"message": "background job failed"})


class _RecordingTransport(Transport):
    events: list[dict[str, Any]] = []

    def capture_envelope(self, envelope: Any) -> None:
        for item in envelope.items:
            if item.headers.get("type") == "event" and item.payload.json:
                self.events.append(item.payload.json)


class _MalformedUpstream(BaseHTTPRequestHandler):
    """200 with a prediction missing `place_id`, so the Places view raises with the address in its locals."""

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "OK", "predictions": [{"description": FAKE_ADDRESS}]}).encode())

    def log_message(self, *_args: Any) -> None:
        pass


@contextmanager
def _recording_sentry(**overrides: Any) -> Iterator[list[dict[str, Any]]]:
    """Init the SDK with the privacy options settings uses; `overrides` swap one out to test a layer alone."""
    global_scope = sentry_sdk.Scope.get_global_scope()
    previous = global_scope.client
    _RecordingTransport.events = []
    sentry_sdk.init(
        dsn="https://public@example.invalid/1",
        integrations=[DjangoIntegration()],
        transport=_RecordingTransport,
        **{**SENTRY_PRIVACY_OPTIONS, **overrides},
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

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.app = get_wsgi_application()

    def setUp(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _MalformedUpstream)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
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

    def _wsgi(self, method: str, path: str, body: dict[str, str] | None = None, query: str = "") -> str:
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
        b"".join(self.app(environ, lambda s, _h, *_a: statuses.append(s)))
        return statuses[0]

    def _assert_clean(self, events: list[dict[str, Any]]) -> None:
        self.assertTrue(events, "expected the unhandled exception to reach Sentry")
        blob = json.dumps(events)
        for leaked in ("Invented", "Nowhere", FAKE_KEY):
            self.assertNotIn(leaked, blob)

    def test_places_post(self) -> None:
        with _recording_sentry() as events:
            status = self._wsgi("POST", "/api/places/autocomplete/", body={"input": FAKE_ADDRESS}, query=ADDRESS_QUERY)
        self.assertTrue(status.startswith("500"), status)
        self._assert_clean(events)

    @patch("screener.views.RemImpactSerializer", side_effect=KeyError("fuel_results"))
    def test_rem_impact_post(self, _serializer: Any) -> None:
        body = {"upgrade": "hvac__heat_pump", "address": FAKE_ADDRESS, "heating_fuel": "natural_gas"}
        with _recording_sentry() as events:
            status = self._wsgi("POST", "/api/screener-options/cesn/rem-impact/", body=body, query=ADDRESS_QUERY)
        self.assertTrue(status.startswith("500"), status)
        self._assert_clean(events)


@override_settings(CACHES=LOCAL_CACHE, ALLOWED_HOSTS=["*"])
class MessageEndpointEventTest(TestCase):
    """Save My Results requests that fail or are refused put no phone number in Sentry.

    Goes through the WSGI app, as `AddressEndpointEventTest` does, so Sentry's own
    integration attaches the request body the way it does in production.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.app = get_wsgi_application()

    def setUp(self) -> None:
        # Django's test client does this too: a raw WSGI call fires request_started and
        # request_finished, whose handler would close the test's database connection
        # mid-transaction.
        for signal in (request_started, request_finished):
            signal.disconnect(close_old_connections)
            self.addCleanup(signal.connect, close_old_connections)

        white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(white_label=white_label, zipcode="78701", household_size=1, completed=True)
        user = User.objects.create_user(email_or_cell="frontend@example.com", password="password")
        user.user_permissions.add(Permission.objects.get(codename="add_message", content_type__app_label="screener"))
        self.token = Token.objects.create(user=user).key
        for target in (
            patch.object(RateWindow, "THROTTLE_RATES", {**RateWindow.THROTTLE_RATES, "message_phone": "1/hour"}),
            patch("screener.views.MessageUser"),
        ):
            target.start()
            self.addCleanup(target.stop)

    def _post(self, phone: str) -> str:
        raw = json.dumps({"screen": str(self.screen.uuid), "phone": phone}).encode()
        environ: dict[str, Any] = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/messages/",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(raw)),
            "HTTP_AUTHORIZATION": f"Token {self.token}",
            "wsgi.input": BytesIO(raw),
        }
        setup_testing_defaults(environ)
        statuses: list[str] = []
        b"".join(self.app(environ, lambda s, _h, *_a: statuses.append(s)))
        return statuses[0]

    def test_an_invalid_phone_reports_without_it(self) -> None:
        with _recording_sentry() as events:
            status = self._post("555-0142")

        self.assertTrue(status.startswith("400"), status)
        self.assertTrue(events, "expected the 400 to reach Sentry")
        self.assertNotIn("555-0142", json.dumps(events))

    @patch("screener.views.MessageUser")
    def test_a_failed_send_reports_without_the_number(self, message_user: Any) -> None:
        # Twilio's own wording for a rejected number, which quotes the number.
        message_user.return_value.send_text.side_effect = RuntimeError(
            "HTTP 400 error: Unable to create record: "
            f"The 'To' number {FAKE_PHONE} is not a valid phone number. (21211)"
        )

        with _recording_sentry() as events:
            status = self._post(FAKE_PHONE)

        self.assertTrue(status.startswith("500"), status)
        self.assertTrue(events, "expected the unhandled exception to reach Sentry")
        blob = json.dumps(events)
        self.assertNotIn("3035550142", blob)
        self.assertIn("21211", blob)

    def test_a_throttled_request_reports_nothing(self) -> None:
        self.assertTrue(self._post(FAKE_PHONE).startswith("201"))

        with _recording_sentry() as events:
            status = self._post(FAKE_PHONE)

        self.assertTrue(status.startswith("429"), status)
        self.assertEqual(events, [])


@override_settings(CACHES=LOCAL_CACHE, ALLOWED_HOSTS=["*"])
class RequestBodyEventTest(TestCase):
    """A DRF error on any endpoint reports without the request body (MFB-2554).

    Goes through the WSGI app, as the other event tests do, so Sentry's own integration
    attaches the body the way it does in production. The endpoint is not special: it is
    not an address or contact endpoint, and its refusal is a plain serializer error, which
    `benefits.views.drf_exception_handler` turns into an event.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.app = get_wsgi_application()

    def setUp(self) -> None:
        for signal in (request_started, request_finished):
            signal.disconnect(close_old_connections)
            self.addCleanup(signal.connect, close_old_connections)

        white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(white_label=white_label, zipcode="78701", household_size=1, completed=True)
        user = User.objects.create_user(email_or_cell="frontend@example.com", password="password")
        user.user_permissions.add(Permission.objects.get(codename="change_screen", content_type__app_label="screener"))
        self.token = Token.objects.create(user=user).key

    def _patch_with_invalid_toggle(self) -> str:
        """PATCH the current-benefits toggle with a value the serializer refuses, plus personal data."""
        body = {"name_abbreviated": "snap", "has": "maybe", "first_name": FAKE_NAME, "email": FAKE_EMAIL}
        raw = json.dumps(body).encode()
        environ: dict[str, Any] = {
            "REQUEST_METHOD": "PATCH",
            "PATH_INFO": f"/api/screens/{self.screen.uuid}/current-benefits/",
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(raw)),
            "HTTP_AUTHORIZATION": f"Token {self.token}",
            "wsgi.input": BytesIO(raw),
        }
        setup_testing_defaults(environ)
        statuses: list[str] = []
        b"".join(self.app(environ, lambda s, _h, *_a: statuses.append(s)))
        return statuses[0]

    def _assert_reported_without_body(self, events: list[dict[str, Any]], status: str) -> None:
        self.assertTrue(status.startswith("400"), status)
        self.assertTrue(events, "expected the 400 to reach Sentry")
        blob = json.dumps(events)
        for leaked in (FAKE_NAME, FAKE_EMAIL):
            self.assertNotIn(leaked, blob)

    def test_the_test_can_see_a_leak(self) -> None:
        # Control: with both layers off, the body is in the event. Without this the tests
        # below would also pass if the request never carried a body into Sentry at all.
        with _recording_sentry(before_send=None, max_request_body_size="always") as events:
            status = self._patch_with_invalid_toggle()

        self.assertTrue(status.startswith("400"), status)
        self.assertIn(FAKE_EMAIL, json.dumps(events))

    def test_production_options_keep_the_body_out(self) -> None:
        with _recording_sentry() as events:
            status = self._patch_with_invalid_toggle()

        self._assert_reported_without_body(events, status)

    def test_the_sdk_option_alone_keeps_the_body_out(self) -> None:
        with _recording_sentry(before_send=None) as events:
            status = self._patch_with_invalid_toggle()

        self._assert_reported_without_body(events, status)

    def test_the_scrubber_alone_keeps_the_body_out(self) -> None:
        with _recording_sentry(max_request_body_size="always") as events:
            status = self._patch_with_invalid_toggle()

        self._assert_reported_without_body(events, status)
