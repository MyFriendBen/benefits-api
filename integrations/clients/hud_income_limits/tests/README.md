# HUD Income Limits Client Tests

This directory contains tests for the HUD Income Limits API client.

## Test Files

### `test_client.py` - Unit Tests (Mocked)
Unit tests that mock all external API calls. These tests:
- Run fast (no network calls)
- Don't require HUD API credentials
- Test client logic, error handling, and edge cases
- Should always pass in CI/CD

**Run unit tests only:**
```bash
pytest integrations/clients/hud_income_limits/tests/test_client.py
```

### `test_integration.py` - Integration Tests (Real API)
Integration tests that make real API calls to HUD. These tests:
- Require valid `HUD_API_TOKEN` environment variable
- Make real network requests (slower)
- Verify actual HUD API behavior
- Should be run in environments with API access

**Run integration tests only:**
```bash
# Requires HUD_API_TOKEN in .env
pytest -m integration integrations/clients/hud_income_limits/tests/
```

**Skip integration tests:**
```bash
pytest -m "not integration" integrations/clients/hud_income_limits/tests/
```

## Test Coverage

### Unit Tests Cover:
- ✅ MTSP AMI lookups for all percentages (20%-100%)
- ✅ Caching behavior (Django cache)
- ✅ Household size validation (1-8)
- ✅ County name normalization
- ✅ Error handling (401, 403, 404, network errors)
- ✅ Missing data scenarios
- ✅ Standard IL placeholder (NotImplementedError)
- ✅ Backward compatibility (`get_screen_ami()` alias)

### Integration Tests Cover:
- ✅ Real API calls to HUD for Cook County, IL
- ✅ Real API calls for Denver County, CO
- ✅ All MTSP percentage levels (20%-100%)
- ✅ Different household sizes (1, 2, 4, 8)
- ✅ Caching with real API responses
- ✅ Invalid county/state error handling
- ✅ Historical year data (2024, 2025)

## Running All Tests

**Run all tests (unit + integration):**
```bash
pytest integrations/clients/hud_income_limits/tests/
```

**Run only unit tests (no API token required):**
```bash
pytest -m "not integration" integrations/clients/hud_income_limits/tests/
```

**Run with coverage:**
```bash
pytest --cov=integrations.clients.hud_income_limits integrations/clients/hud_income_limits/tests/
```

## CI/CD Configuration

For CI/CD pipelines:

```yaml
# Run unit tests (fast, no API token)
- pytest -m "not integration" integrations/clients/hud_income_limits/tests/

# Optionally run integration tests if HUD_API_TOKEN is available
- pytest -m integration integrations/clients/hud_income_limits/tests/
```

## Adding New Tests

When adding new functionality to the HUD client:

1. **Add unit tests first** - Mock the API responses
2. **Add integration tests** - Verify with real API (if applicable)
3. **Update this README** - Document what's covered

## Test Data

Unit tests use mocked HUD API responses for:
- **Cook County, IL** (FIPS: 17031)
- **Household size 4**
- **Year 2025**
- **All MTSP percentage levels**

Integration tests use real API calls for:
- **Cook County, IL** (high-cost urban area)
- **Denver County, CO** (medium-cost urban area)
- **Years 2024-2025**

## Troubleshooting

**Integration tests failing with "HUD_API_TOKEN not set":**
- Add `HUD_API_TOKEN=your_token` to `.env`
- Get token at: https://www.huduser.gov/hudapi/public/register
- Register for both FMR and Income Limits datasets

**Integration tests timing out:**
- Check internet connection
- Verify HUD API is accessible
- Check token has correct dataset permissions

**Cache-related test failures:**
- Tests clear cache in `setUp()` to avoid interference
- If issues persist, manually clear Django cache
