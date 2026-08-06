"""
Pytest configuration for integration tests with VCR.

This module configures VCR (Video Cassette Recorder) to record and replay
HTTP interactions during tests. It automatically scrubs sensitive information
from cassettes using VCR's built-in filtering capabilities.

VCR behavior controlled by VCR_MODE environment variable:
- VCR_MODE=new_episodes (PRs): Replays existing interactions, records NEW HTTP requests not in cassette
- VCR_MODE=all (push to main): Never replays, re-records ALL cassettes from scratch
- VCR_MODE=once (local default): Replays existing interactions, ERRORS if cassette missing new HTTP request
- VCR_MODE=none (strict playback): Replays only, never records, errors on any new HTTP requests

All integration tests marked with @pytest.mark.integration automatically use VCR.

Two integrations use this harness:
- HUD income limits (integrations/clients/hud_income_limits) — needs HUD_API_TOKEN to record
- PolicyEngine program spec-scenario tests — see programs/programs/policyengine/tests/
  spec_scenarios.py and docs/TESTING.md
"""

import json
import logging
import os
import re
from typing import Optional

import pytest
import vcr as vcrpy
from decouple import config

logger = logging.getLogger(__name__)

# PolicyEngine's household endpoint. Every program's eligibility comes from a POST to the
# same URL, so cassette matching for this host has to consider the request body — see
# policy_engine_body().
PE_API_HOST = "household.api.policyengine.org"

# Tests that need real HUD credentials to record. Used to scope the no-token skip below to
# HUD only, instead of disabling every integration test in the suite.
HUD_TEST_PATH_FRAGMENT = "hud_income_limits"

# Hosts VCR passes straight through, never recording. PolicyEngine's OAuth exchange lives
# here: its response body is a real bearer token, so it must not be written to a cassette.
# Recording fetches a token live; replay pre-seeds a placeholder instead (see
# programs/programs/policyengine/tests/spec_scenarios.py).
VCR_IGNORE_HOSTS = ["policyengine.uk.auth0.com"]


# Sensitive headers to redact in VCR cassettes
SENSITIVE_HEADERS = [
    "authorization",
    "x-api-key",
    "api-key",
    "apikey",
    "x-auth-token",
    "auth-token",
    "cookie",
    "set-cookie",
]

# Sensitive query parameters to redact
SENSITIVE_QUERY_PARAMS = [
    "api_key",
    "apikey",
    "token",
    "auth",
    "api-key",
]

# Sensitive POST data parameters to redact
SENSITIVE_POST_PARAMS = [
    "api_key",
    "apiKey",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "client_secret",
    "secret",
    "password",
]


def scrub_response_body(response):
    """
    Scrub sensitive data from response bodies that VCR can't auto-detect.

    This handles dynamic patterns in response bodies:
    - Bearer tokens in Authorization header values within JSON
    - Email addresses (PII) in error messages
    - IP addresses in error messages
    - File paths and stack traces in error responses

    VCR's built-in filters already handle:
    - Headers (via filter_headers)
    - Query parameters (via filter_query_parameters)
    - POST data (via filter_post_data_parameters)

    Args:
        response: VCR response object

    Returns:
        Modified response with sensitive data redacted, or None to skip recording
    """
    if "body" not in response or "string" not in response["body"]:
        return response

    body = response["body"]["string"]
    if isinstance(body, bytes):
        body_str = body.decode("utf-8", errors="ignore")
    else:
        body_str = body

    # Only scrub patterns that VCR can't handle with built-in filters
    patterns = [
        # Bearer tokens embedded in response bodies (e.g., JSON with auth info)
        (r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer REDACTED"),
        # Email addresses (PII in error messages)
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "user@REDACTED.com"),
        # IP addresses in error messages
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "XXX.XXX.XXX.XXX"),
    ]

    for pattern, replacement in patterns:
        body_str = re.sub(pattern, replacement, body_str, flags=re.IGNORECASE)

    # Scrub error response details (status >= 400)
    if "status" in response and "code" in response["status"]:
        status_code = response["status"]["code"]
        if status_code >= 400:
            # Scrub stack traces and internal paths
            body_str = re.sub(r'File "([^"]*)"', 'File "REDACTED"', body_str)
            body_str = re.sub(r"(/[a-zA-Z0-9_\-./]+/[a-zA-Z0-9_\-./]+)", "REDACTED_PATH", body_str)

    # Convert back to original type
    if isinstance(body, bytes):
        response["body"]["string"] = body_str.encode("utf-8")
    else:
        response["body"]["string"] = body_str

    return response


def _json_body(request):
    """Parse a VCR request body as JSON, falling back to the raw bytes if it isn't JSON."""
    body = request.body
    if body is None:
        return None
    if isinstance(body, bytes):
        try:
            body = body.decode("utf-8")
        except UnicodeDecodeError:
            return request.body
    try:
        return json.loads(body)
    except (TypeError, ValueError):
        return body


def cassette_name(request) -> str:
    """Cassette filename for a test, qualified by its class when it has one.

    The bare test name is ambiguous: two identically-named methods in different classes in
    the same module would share one cassette and silently replay each other's recording.
    Class-qualifying makes the filename unique for every test that can exist in a module.
    """
    test_class = getattr(request.node, "cls", None)
    if test_class is None:
        return f"{request.node.name}.yaml"

    return f"{test_class.__name__}.{request.node.name}.yaml"


def policy_engine_body(r1, r2):
    """Match PolicyEngine requests on their body; ignore every other host.

    All PolicyEngine calls go to the same URL (POST household.api.../us/calculate): the
    household and the pinned model version travel in the JSON body. Matching only on
    method/path would make a cassette replay its recorded response for *any* payload, so a
    regression in how we assemble the request would replay the old answer and still pass —
    exactly the wiring bug these tests exist to catch.

    Household member ids are compared as recorded, deliberately un-normalized. The response
    is keyed by those same ids (PrivateApiSim.value reads result[unit][member_id]), so a
    cassette recorded under different primary keys cannot be replayed at all. A clean "no
    matching request" error is the honest signal; see docs/TESTING.md on assigning explicit
    primary keys in PolicyEngine tests.

    Non-PolicyEngine requests return a match here and are still discriminated by the other
    matchers (method/scheme/host/port/path/query), so existing cassettes are unaffected.
    """
    if r1.host != PE_API_HOST and r2.host != PE_API_HOST:
        return True

    body1 = _json_body(r1)
    body2 = _json_body(r2)
    if body1 != body2:
        raise AssertionError(
            "PolicyEngine request body does not match the recorded cassette. Either the "
            "household/version changed (re-record the cassette) or the test's primary keys "
            "differ from the recorded ones (assign explicit ids)."
        )
    return True


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Stash each phase's report on the item so fixtures can see whether the test failed.

    Needed because pytest does not throw a test's exception into a fixture generator: the
    generator simply resumes at teardown. A fixture that opens a resource around ``yield``
    (``auto_vcr`` and its cassette) therefore cannot tell a pass from a failure on its own,
    and VCR's own ``record_on_exception`` never fires. See ``auto_vcr``.
    """
    report = yield
    setattr(item, f"rep_{report.when}", report)
    return report


def _test_failed(request) -> bool:
    """Whether the test body itself failed (as opposed to setup or teardown)."""
    report = getattr(request.node, "rep_call", None)

    return report is not None and report.failed


def _discard_failed_recording(cassette_path: str, contents_before: Optional[bytes]) -> None:
    """Undo any cassette write made by a failing test.

    A failed recording — bad credentials, a 4xx, an unserved API version — otherwise leaves
    a cassette holding the error response, which then replays forever and reads as a code
    failure rather than as the recording problem it was. Restores the previous contents, or
    removes the file if the test created it.
    """
    if contents_before is None:
        if os.path.exists(cassette_path):
            os.remove(cassette_path)
            logger.warning("Discarded cassette recorded by a failing test: %s", cassette_path)
        return

    if not os.path.exists(cassette_path):
        return

    with open(cassette_path, "rb") as f:
        if f.read() == contents_before:
            return

    with open(cassette_path, "wb") as f:
        f.write(contents_before)
    logger.warning("Reverted cassette modified by a failing test: %s", cassette_path)


@pytest.fixture(scope="module")
def vcr_config(request):
    """
    Configure VCR with security-focused defaults.

    Cassettes are stored in a 'cassettes' directory next to the test file.
    For example: integrations/clients/hud_income_limits/tests/cassettes/

    Args:
        request: pytest request object to get test file path

    Returns:
        dict: VCR configuration options
    """
    # Get the directory containing the test file
    test_dir = os.path.dirname(str(request.fspath))
    cassette_dir = os.path.join(test_dir, "cassettes")

    return {
        "cassette_library_dir": cassette_dir,
        "record_mode": "once",  # Record once, then replay. Use 'new_episodes' to add new interactions
        # policy_engine_body is a no-op for every host except PolicyEngine, whose requests
        # are only distinguishable by their body (registered in auto_vcr).
        "match_on": ["method", "scheme", "host", "port", "path", "query", "policy_engine_body"],
        # Use VCR's built-in filtering for headers, query params, and POST data
        "filter_headers": SENSITIVE_HEADERS,
        "filter_query_parameters": SENSITIVE_QUERY_PARAMS,
        "filter_post_data_parameters": SENSITIVE_POST_PARAMS,
        "ignore_hosts": VCR_IGNORE_HOSTS,
        # Only use custom scrubbing for response body patterns VCR can't auto-detect
        "before_record_response": scrub_response_body,
        "decode_compressed_response": True,  # Auto-decompress gzipped responses
        # Don't write a cassette when the test raises. Belt-and-braces only: VCR checks this
        # in Cassette.__exit__, keyed on an exception propagating out of the `with` block,
        # and pytest never throws a test failure into a fixture generator — so for a cassette
        # opened inside auto_vcr this never fires. The discard in auto_vcr is what actually
        # keeps a failed recording out of the repo.
        "record_on_exception": False,
    }


@pytest.fixture(autouse=True)
def auto_vcr(request, vcr_config):
    """
    Automatically apply VCR to integration tests.

    This fixture:
    - Detects if a test is marked with @pytest.mark.integration
    - Automatically uses VCR to record/replay HTTP interactions
    - VCR_MODE=new_episodes (PRs): Flexible - replays existing, records new HTTP requests not yet in cassette
    - VCR_MODE=all (push to main): Fresh start - never replays, re-records all cassettes from scratch
    - VCR_MODE=once (local default): Strict - replays existing cassettes, errors if test makes new HTTP request
    - VCR_MODE=none (strict playback): Read-only - replays only, never records, errors on new HTTP requests

    Cassettes are stored in: <test_dir>/cassettes/<TestClass>.<test_name>.yaml
    Example: integrations/clients/hud_income_limits/tests/cassettes/
             TestHudIntegrationMTSP.test_real_api_call_cook_county_il.yaml

    Anything recorded by a failing test is discarded on teardown, so a bad recording can't
    leave an error response behind to replay (see _discard_failed_recording).

    Args:
        request: pytest request object
        vcr_config: VCR configuration dict
    """
    marker = request.node.get_closest_marker("integration")

    # Only apply VCR to integration-marked tests
    if not marker:
        yield
        return

    # Determine VCR record mode based on VCR_MODE environment variable
    # Possible values:
    #   - "new_episodes": Flexible - replays existing, records new HTTP requests (PRs in CI)
    #   - "all": Fresh start - never replays, re-records everything from scratch (push to main in CI)
    #   - "once" (default): Strict - replays existing, errors if cassette missing new HTTP request (local dev)
    #   - "none": Read-only - replays only, never records, errors on new HTTP requests (strict mode)
    vcr_mode = os.getenv("VCR_MODE", "once").lower()

    # Validate and use the mode
    valid_modes = ["none", "new_episodes", "all", "once"]
    record_mode = vcr_mode if vcr_mode in valid_modes else "once"

    # Log VCR configuration for visibility in CI
    logger.info(f"VCR mode: {record_mode} | Test: {request.node.name}")

    # Create VCR instance and use cassette. Custom matchers must be registered on the
    # instance before the cassette is used (match_on names are resolved lazily).
    vcr = vcrpy.VCR(**vcr_config)
    vcr.register_matcher("policy_engine_body", policy_engine_body)

    # Snapshot the cassette so a failing test's recording can be thrown away afterwards.
    # record_on_exception can't do this from inside a fixture — see pytest_runtest_makereport.
    cassette_path = os.path.join(vcr_config["cassette_library_dir"], cassette_name(request))
    contents_before = None
    if os.path.exists(cassette_path):
        with open(cassette_path, "rb") as f:
            contents_before = f.read()

    with vcr.use_cassette(cassette_name(request), record_mode=record_mode):
        yield

    if _test_failed(request):
        _discard_failed_recording(cassette_path, contents_before)


@pytest.fixture(autouse=True)
def clear_cache():
    """Start every test with an empty cache.

    LocMemCache gives each process its own cache, so isolation was implicit while
    CI set no REDIS_URL. Against a real Redis the state outlives both the test and
    the run, which makes order-dependent passes and stale-value failures easy to
    introduce. Note this flushes the configured cache database, so pointing
    REDIS_URL at a Redis you also use for development will clear it.
    """
    from django.core.cache import cache

    cache.clear()
    yield


@pytest.fixture
def integration_requires_token():
    """
    Skip integration test if HUD_API_TOKEN is not available.

    Use this in tests that absolutely require real API credentials:

    @pytest.mark.integration
    def test_something(integration_requires_token):
        # Test code that needs HUD_API_TOKEN
        ...
    """
    has_token = bool(config("HUD_API_TOKEN", default=None))
    if not has_token:
        pytest.skip("HUD_API_TOKEN not set - skipping integration test")


def _requires_hud_token(item) -> bool:
    """Whether an integration test needs real HUD credentials.

    Scoped by test location and by use of the ``integration_requires_token`` fixture rather
    than by the ``integration`` marker, which other integrations (PolicyEngine) also use.
    """
    if HUD_TEST_PATH_FRAGMENT in str(getattr(item, "fspath", "")):
        return True

    return "integration_requires_token" in getattr(item, "fixturenames", ())


def pytest_collection_modifyitems(config, items):
    """
    Skip HUD integration tests when no API token is configured.

    Fork PR workflows do not receive repository secrets, so ``HUD_API_TOKEN`` is
    unset. Unittest TestCase subclasses do not always honor ``pytest_runtest_setup``;
    applying a skip marker at collection time is reliable.

    Only HUD tests are skipped. Integration tests for other services replay from their
    cassettes without credentials, and skipping them here would silently report them as
    green while never running them.
    """
    from decouple import config as decouple_config

    token = decouple_config("HUD_API_TOKEN", default=None)
    if token:
        return
    skip_integration = pytest.mark.skip(reason="HUD_API_TOKEN not set - skipping HUD integration tests")
    for item in items:
        if item.get_closest_marker("integration") and _requires_hud_token(item):
            item.add_marker(skip_integration)
