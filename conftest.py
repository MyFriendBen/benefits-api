"""
Pytest configuration for integration tests with VCR.

This module configures VCR (Video Cassette Recorder) to record and replay
HTTP interactions during tests. It automatically scrubs sensitive information
from cassettes to prevent accidental credential leaks.

VCR behavior controlled by VCR_MODE environment variable:
- VCR_MODE=new_episodes (PRs): Records new interactions only, replays existing cassettes
- VCR_MODE=all (push to main): Re-records ALL cassettes to verify API interface
- VCR_MODE=once (local default): Records new cassettes if missing, replays existing
- VCR_MODE=none (strict playback): Uses existing cassettes only, no real API calls

All integration tests marked with @pytest.mark.integration automatically use VCR.
"""

import os
import re
import pytest
import vcr as vcrpy
from decouple import config


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


def scrub_sensitive_data(response):
    """
    Scrub sensitive data from VCR cassettes.

    This function redacts:
    - Authorization headers
    - API keys in headers
    - API keys in request/response bodies
    - Tokens in URLs and bodies (access, refresh, ID tokens)
    - Client secrets and credentials
    - Sensitive data in error responses
    - Email addresses and PII in error messages

    Args:
        response: VCR response object

    Returns:
        Modified response with sensitive data redacted
    """
    # Scrub headers
    if "headers" in response:
        for header in response["headers"]:
            if header.lower() in SENSITIVE_HEADERS:
                response["headers"][header] = ["REDACTED"]

    # Scrub body content (if it's a string)
    if "body" in response and "string" in response["body"]:
        body = response["body"]["string"]
        if isinstance(body, bytes):
            body_str = body.decode("utf-8", errors="ignore")
        else:
            body_str = body

        # Enhanced patterns for tokens/keys in bodies
        patterns = [
            # API keys and tokens
            (r'"api_key"\s*:\s*"[^"]*"', '"api_key": "REDACTED"'),
            (r'"apiKey"\s*:\s*"[^"]*"', '"apiKey": "REDACTED"'),
            (r'"token"\s*:\s*"[^"]*"', '"token": "REDACTED"'),
            (r'"access_token"\s*:\s*"[^"]*"', '"access_token": "REDACTED"'),
            (r'"refresh_token"\s*:\s*"[^"]*"', '"refresh_token": "REDACTED"'),
            (r'"id_token"\s*:\s*"[^"]*"', '"id_token": "REDACTED"'),
            (r'"authorization"\s*:\s*"[^"]*"', '"authorization": "REDACTED"'),
            (r'"client_secret"\s*:\s*"[^"]*"', '"client_secret": "REDACTED"'),
            (r'"secret"\s*:\s*"[^"]*"', '"secret": "REDACTED"'),
            (r'"password"\s*:\s*"[^"]*"', '"password": "REDACTED"'),
            # Bearer tokens in various formats
            (r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer REDACTED"),
            # Email addresses (PII in error messages)
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "user@REDACTED.com"),
            # IP addresses in error messages
            (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "XXX.XXX.XXX.XXX"),
        ]

        for pattern, replacement in patterns:
            body_str = re.sub(pattern, replacement, body_str, flags=re.IGNORECASE)

        # Sanitize error response bodies (preserve error structure but remove sensitive details)
        # Check if this is an error response (status >= 400)
        if "status" in response and "code" in response["status"]:
            status_code = response["status"]["code"]
            if status_code >= 400:
                # Scrub stack traces and internal paths from error responses
                body_str = re.sub(r'File "([^"]*)"', 'File "REDACTED"', body_str)
                # Scrub internal server paths
                body_str = re.sub(r"(/[a-zA-Z0-9_\-./]+/[a-zA-Z0-9_\-./]+)", "REDACTED_PATH", body_str)

        # Convert back to bytes if original was bytes
        if isinstance(body, bytes):
            response["body"]["string"] = body_str.encode("utf-8")
        else:
            response["body"]["string"] = body_str

    return response


def scrub_request(request):
    """
    Scrub sensitive data from VCR request recordings.

    Args:
        request: VCR request object

    Returns:
        Modified request with sensitive data redacted
    """
    # Scrub query parameters that might contain keys from URI
    if hasattr(request, "uri"):
        # Remove API keys from query strings
        request.uri = re.sub(
            r"([?&])(api[_-]?key|token|auth)=[^&]*", r"\1\2=REDACTED", request.uri, flags=re.IGNORECASE
        )

    # Scrub headers
    if hasattr(request, "headers"):
        for header in request.headers:
            if header.lower() in SENSITIVE_HEADERS:
                request.headers[header] = "REDACTED"

    # Scrub body if present
    if hasattr(request, "body") and request.body:
        body = request.body
        if isinstance(body, bytes):
            body_str = body.decode("utf-8", errors="ignore")
        elif isinstance(body, str):
            body_str = body
        else:
            return request

        # Replace tokens in body
        patterns = [
            (r'"api_key"\s*:\s*"[^"]*"', '"api_key": "REDACTED"'),
            (r'"token"\s*:\s*"[^"]*"', '"token": "REDACTED"'),
        ]

        for pattern, replacement in patterns:
            body_str = re.sub(pattern, replacement, body_str, flags=re.IGNORECASE)

        if isinstance(body, bytes):
            request.body = body_str.encode("utf-8")
        else:
            request.body = body_str

    return request


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
        "filter_headers": SENSITIVE_HEADERS,
        "filter_query_parameters": [
            "api_key",
            "apikey",
            "token",
            "auth",
        ],
        "before_record_request": scrub_request,
        "before_record_response": scrub_sensitive_data,
        "decode_compressed_response": True,  # Auto-decompress gzipped responses
    }


@pytest.fixture(scope="module")
def vcr_instance(vcr_config):
    """
    Create a VCR instance with our configuration.

    Returns:
        VCR: Configured VCR instance
    """
    return vcrpy.VCR(**vcr_config)


@pytest.fixture(autouse=True)
def auto_vcr(request, vcr_instance):
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
        vcr_instance: Configured VCR instance
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

    # Use VCR cassette - named after the test
    cassette_name = f"{request.node.name}.yaml"
    with vcr_instance.use_cassette(cassette_name, record_mode=record_mode):
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
