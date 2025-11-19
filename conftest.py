"""
Pytest configuration for integration tests with VCR.

This module configures VCR (Video Cassette Recorder) to record and replay
HTTP interactions during tests. It automatically scrubs sensitive information
from cassettes to prevent accidental credential leaks.

Integration tests run with real API calls when:
- RUN_REAL_INTEGRATION_TESTS environment variable is set
- Running locally with actual credentials

Integration tests use VCR cassettes when:
- Running in CI without RUN_REAL_INTEGRATION_TESTS flag
- Running locally without credentials
"""

import os
import re
import pytest
import vcr as vcrpy
from decouple import config


def scrub_sensitive_data(response):
    """
    Scrub sensitive data from VCR cassettes.

    This function redacts:
    - Authorization headers
    - API keys in headers
    - API keys in request/response bodies
    - Tokens in URLs and bodies
    - Any HUD API specific credentials

    Args:
        response: VCR response object

    Returns:
        Modified response with sensitive data redacted
    """
    # Scrub headers
    sensitive_headers = [
        "authorization",
        "x-api-key",
        "api-key",
        "apikey",
        "x-auth-token",
        "auth-token",
        "cookie",
        "set-cookie",
    ]

    if "headers" in response:
        for header in sensitive_headers:
            # Check both lowercase and original case
            if header in response["headers"]:
                response["headers"][header] = ["REDACTED"]
            # Also check capitalized versions
            header_title = header.title()
            if header_title in response["headers"]:
                response["headers"][header_title] = ["REDACTED"]

    # Scrub body content (if it's a string)
    if "body" in response and "string" in response["body"]:
        body = response["body"]["string"]
        if isinstance(body, bytes):
            body_str = body.decode("utf-8", errors="ignore")
        else:
            body_str = body

        # Replace common patterns for tokens/keys in bodies
        patterns = [
            (r'"api_key"\s*:\s*"[^"]*"', '"api_key": "REDACTED"'),
            (r'"apiKey"\s*:\s*"[^"]*"', '"apiKey": "REDACTED"'),
            (r'"token"\s*:\s*"[^"]*"', '"token": "REDACTED"'),
            (r'"access_token"\s*:\s*"[^"]*"', '"access_token": "REDACTED"'),
            (r'"authorization"\s*:\s*"[^"]*"', '"authorization": "REDACTED"'),
        ]

        for pattern, replacement in patterns:
            body_str = re.sub(pattern, replacement, body_str, flags=re.IGNORECASE)

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
    sensitive_headers = [
        "authorization",
        "x-api-key",
        "api-key",
        "apikey",
        "x-auth-token",
        "auth-token",
    ]

    if hasattr(request, "headers"):
        for header in sensitive_headers:
            if header in request.headers:
                request.headers[header] = "REDACTED"
            header_title = header.title()
            if header_title in request.headers:
                request.headers[header_title] = "REDACTED"

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
        "filter_headers": [
            "authorization",
            "x-api-key",
            "api-key",
            "cookie",
            "set-cookie",
        ],
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
    Automatically apply VCR to integration tests in CI mode.

    This fixture:
    - Detects if a test is marked with @pytest.mark.integration
    - In CI (without RUN_REAL_INTEGRATION_TESTS), uses VCR cassettes
    - Outside CI or with RUN_REAL_INTEGRATION_TESTS, makes real API calls
    - Creates cassette files in a 'cassettes' directory next to the test file

    Cassettes are stored in: <test_dir>/cassettes/<test_name>.yaml
    For example: integrations/clients/hud_income_limits/tests/cassettes/test_real_api_call_cook_county_il.yaml

    Args:
        request: pytest request object
        vcr_instance: Configured VCR instance
    """
    marker = request.node.get_closest_marker("integration")

    # Only apply VCR to integration-marked tests
    if not marker:
        yield
        return

    # Check if we should use real API calls
    use_real_calls = not os.getenv("CI") or os.getenv(  # Not in CI
        "RUN_REAL_INTEGRATION_TESTS"
    )  # Explicit flag to use real calls

    if use_real_calls:
        # Run test with real API calls
        yield
    else:
        # Use VCR cassette - named after the test
        cassette_name = f"{request.node.name}.yaml"
        with vcr_instance.use_cassette(cassette_name):
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
