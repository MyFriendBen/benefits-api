# Integration Testing Guide

This guide explains how to write, run, and maintain integration tests in the benefits-api codebase.

## Overview

Integration tests verify that our code works correctly with real external APIs. We use [VCR.py](https://vcrpy.readthedocs.io/) to record and replay HTTP interactions, allowing tests to run quickly in CI without requiring API credentials.

## How It Works

### VCR Cassettes

VCR (Video Cassette Recorder) records HTTP interactions the first time a test runs with real API credentials, then replays those recordings on subsequent runs. This provides:

- **Fast tests**: No network calls in CI
- **No credentials needed in CI**: Tests run using recorded cassettes
- **Reproducible results**: Same responses every time
- **Cost savings**: Fewer API calls to metered services

### Automatic Security Scrubbing

All sensitive information is **automatically removed** from cassettes before they're saved:

- Authorization headers (including `Authorization`, `X-API-Key`, etc.)
- API tokens in query parameters
- Credentials in request/response bodies
- Cookies and session tokens

This scrubbing is configured in the root `conftest.py` and happens automatically - you don't need to manually edit cassettes.

## Writing Integration Tests

### 1. Mark Tests with `@pytest.mark.integration`

```python
import pytest
from django.test import TestCase

@pytest.mark.integration
class TestMyAPIIntegration(TestCase):
    """Integration tests for My API client."""

    def test_api_call(self):
        # Your test code here
        result = my_api_client.fetch_data()
        assert result is not None
```

### 2. Organize Cassettes

Cassettes are stored in a `cassettes/` directory next to your test file:

```
integrations/clients/my_api/
├── tests/
│   ├── cassettes/
│   │   ├── .gitignore
│   │   ├── test_fetch_data.yaml
│   │   └── test_error_handling.yaml
│   ├── test_client.py         # Unit tests (mocked)
│   └── test_integration.py    # Integration tests (real API or VCR)
├── __init__.py
└── client.py
```

### 3. Use `@skipUnless` for Optional Credentials

If a test should skip when credentials aren't available:

```python
from unittest import skipUnless
from decouple import config

@pytest.mark.integration
class TestMyAPIIntegration(TestCase):

    @skipUnless(config("MY_API_TOKEN", default=None), "MY_API_TOKEN not set")
    def test_with_real_api(self):
        # This test will be skipped if MY_API_TOKEN is not in .env
        pass
```

## Running Integration Tests

### Run All Integration Tests

```bash
pytest -m integration
```

### Skip Integration Tests (Run Only Unit Tests)

```bash
pytest -m "not integration"
```

### Force Real API Calls (Bypass VCR)

```bash
RUN_REAL_INTEGRATION_TESTS=true pytest -m integration
```

### Run a Specific Integration Test

```bash
pytest -m integration integrations/clients/hud_income_limits/tests/test_integration.py::TestHudIntegrationMTSP::test_real_api_call_cook_county_il
```

## When VCR is Used

VCR behavior depends on the environment:

| Environment | VCR Behavior |
|-------------|--------------|
| **CI (GitHub Actions)** | Always uses cassettes (unless `RUN_REAL_INTEGRATION_TESTS=true`) |
| **Locally with API credentials** | Makes real API calls, updates cassettes |
| **Locally without credentials** | Uses existing cassettes |

## Recording or Updating Cassettes

When you need to create new cassettes or update existing ones:

### Step 1: Add API Credentials

Add the required API token to your `.env` file:

```bash
# .env
HUD_API_TOKEN=your_actual_token_here
```

### Step 2: Delete Old Cassette (if updating)

```bash
rm integrations/clients/hud_income_limits/tests/cassettes/test_real_api_call_cook_county_il.yaml
```

### Step 3: Run the Test

```bash
pytest -m integration integrations/clients/hud_income_limits/tests/test_integration.py::TestHudIntegrationMTSP::test_real_api_call_cook_county_il
```

The test will:
1. Make a real API call
2. Record the HTTP interaction
3. Automatically scrub sensitive data
4. Save the cassette to `cassettes/test_real_api_call_cook_county_il.yaml`

### Step 4: Review the Cassette

**IMPORTANT**: Always review the cassette file before committing:

```bash
# Look for "REDACTED" to confirm scrubbing worked
grep -i "authorization\|api.key\|token" integrations/clients/hud_income_limits/tests/cassettes/test_real_api_call_cook_county_il.yaml
```

You should see values like `REDACTED` instead of actual tokens.

### Step 5: Commit the Cassette

```bash
git add integrations/clients/hud_income_limits/tests/cassettes/test_real_api_call_cook_county_il.yaml
git commit -m "Update HUD API cassette for Cook County test"
```

## Best Practices

### ✅ Do

- **Mark all integration tests** with `@pytest.mark.integration`
- **Keep cassettes committed** to git (they're safe - credentials are scrubbed)
- **Use descriptive test names** - they become cassette filenames
- **Review cassettes before committing** - verify scrubbing worked
- **Update cassettes when APIs change** - delete and re-record
- **Test both success and error cases** - record error responses too

### ❌ Don't

- **Don't edit cassettes manually** - regenerate them instead
- **Don't commit cassettes without reviewing them** - always check for leaked secrets
- **Don't skip the `@pytest.mark.integration` decorator** - VCR won't activate
- **Don't put credentials in test code** - use environment variables
- **Don't make integration tests the default** - prefer unit tests with mocks

## Troubleshooting

### Test Fails: "Could not find cassette"

**Cause**: No cassette exists and VCR is in playback mode (CI or no credentials).

**Solution**:
1. Add API credentials to `.env`
2. Run the test to record a new cassette
3. Commit the cassette

### Test Fails: "Request did not match"

**Cause**: The API request changed (different URL, params, or headers) but the cassette has the old version.

**Solution**: Delete the cassette and re-record with current API credentials.

### Cassette Contains Sensitive Data

**Cause**: The scrubbing function in `conftest.py` doesn't cover this type of credential.

**Solution**:
1. **DO NOT COMMIT** the cassette
2. Update `scrub_request()` or `scrub_sensitive_data()` in `conftest.py`
3. Delete the cassette and re-record

### Integration Test Runs in CI Without Cassette

**Cause**: The cassette file wasn't committed to git.

**Solution**:
```bash
git add integrations/clients/*/tests/cassettes/*.yaml
git commit -m "Add missing cassettes"
```

## Advanced Configuration

### Custom VCR Settings

The VCR configuration is in the root `conftest.py`. You can customize:

- `record_mode`: How VCR handles new requests
  - `"once"`: Record new cassettes, replay existing (default)
  - `"new_episodes"`: Add new interactions to existing cassettes
  - `"all"`: Always record, overwrite cassettes
  - `"none"`: Never record, only replay
- `match_on`: How VCR matches requests (method, URL, headers, body, etc.)
- Filter rules for headers and query parameters

### Per-Test VCR Configuration

If you need custom VCR behavior for a specific test, you can use the `vcr_instance` fixture:

```python
@pytest.mark.integration
def test_with_custom_vcr(vcr_instance):
    with vcr_instance.use_cassette('my_custom_cassette.yaml', record_mode='all'):
        # This test will always re-record
        result = my_api_client.fetch()
```

## Examples

See these files for examples:
- [integrations/clients/hud_income_limits/tests/test_integration.py](../integrations/clients/hud_income_limits/tests/test_integration.py) - Full integration test suite
- [conftest.py](../conftest.py) - VCR configuration and security scrubbing
