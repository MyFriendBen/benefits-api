"""
Pytest configuration for integration tests with VCR.

This module configures VCR (Video Cassette Recorder) to record and replay
HTTP interactions during tests. It automatically scrubs sensitive information
from cassettes using VCR's built-in filtering capabilities.

VCR behavior controlled by VCR_MODE environment variable:
- VCR_MODE=new_episodes (PRs): Records new interactions only, replays existing cassettes
- VCR_MODE=all (push to main): Re-records ALL cassettes to verify API interface
- VCR_MODE=once (local default): Records new cassettes if missing, replays existing
- VCR_MODE=none (strict playback): Uses existing cassettes only, no real API calls

All integration tests marked with @pytest.mark.integration automatically use VCR.
"""

import logging
import os
import re
import pytest
import vcr as vcrpy
from decouple import config

logger = logging.getLogger(__name__)


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
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        # Use VCR's built-in filtering for headers, query params, and POST data
        "filter_headers": SENSITIVE_HEADERS,
        "filter_query_parameters": SENSITIVE_QUERY_PARAMS,
        "filter_post_data_parameters": SENSITIVE_POST_PARAMS,
        # Only use custom scrubbing for response body patterns VCR can't auto-detect
        "before_record_response": scrub_response_body,
        "decode_compressed_response": True,  # Auto-decompress gzipped responses
    }


@pytest.fixture(autouse=True)
def auto_vcr(request, vcr_config):
    """
    Automatically apply VCR to integration tests.

    This fixture:
    - Detects if a test is marked with @pytest.mark.integration
    - Automatically uses VCR to record/replay HTTP interactions
    - VCR_MODE=none (PRs): Playback-only mode, uses existing cassettes
    - VCR_MODE=new_episodes (push to main): Makes real API calls, updates cassettes with new data
    - VCR_MODE=once (local default): Records new cassettes if missing, replays existing ones
    - VCR_MODE=all (force re-record): Forces complete re-recording

    Cassettes are stored in: <test_dir>/cassettes/<test_name>.yaml
    Example: integrations/clients/hud_income_limits/tests/cassettes/test_real_api_call_cook_county_il.yaml

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
    #   - "new_episodes": Record new interactions only, replay existing (PRs in CI)
    #   - "all": Re-record all cassettes to verify API interface (push to main in CI)
    #   - "once" (default): Record if missing, replay otherwise (local dev)
    #   - "none": Strict playback only, no recording at all
    vcr_mode = os.getenv("VCR_MODE", "once").lower()

    # Validate and use the mode
    valid_modes = ["none", "new_episodes", "all", "once"]
    record_mode = vcr_mode if vcr_mode in valid_modes else "once"

    # Log VCR configuration for visibility in CI
    logger.info(f"VCR mode: {record_mode} | Test: {request.node.name}")

    # Create VCR instance and use cassette
    vcr = vcrpy.VCR(**vcr_config)
    cassette_name = f"{request.node.name}.yaml"
    with vcr.use_cassette(cassette_name, record_mode=record_mode):
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
    has_token = config("HUD_API_TOKEN", default=None) is not None
    if not has_token:
        pytest.skip("HUD_API_TOKEN not set - skipping integration test")
