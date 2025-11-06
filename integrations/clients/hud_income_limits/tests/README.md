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

**Test Class Organization:**
- `TestHudIntegrationMTSP` - MTSP endpoint functionality tests
- `TestHudIntegrationStandardIL` - Standard Section 8 IL endpoint functionality tests
- `TestHudIntegrationErrors` - Error handling tests for both endpoints

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
- ✅ Standard Section 8 IL AMI lookups (30%, 50%, 80%)
- ✅ Caching behavior (Django cache) for both endpoints
- ✅ Household size validation (1-8)
- ✅ County name normalization
- ✅ Error handling (401, 403, 404, network errors)
- ✅ Missing data scenarios for both MTSP and Standard IL
- ✅ Type aliases (`MtspAmiPercent`, `Section8AmiPercent`)
- ✅ County FIPS code lookup with year parameter

### Integration Tests Cover:

**MTSP Endpoint:**
- ✅ Real API calls to HUD for Cook County, IL
- ✅ Real API calls for Denver County, CO
- ✅ All MTSP percentage levels (20%-100%)
- ✅ Different household sizes (1, 2, 4, 8)
- ✅ Caching with real API responses
- ✅ Historical year data (2024, 2025)
- ✅ Hold-harmless verification (2025 ≥ 2024)

**Standard Section 8 IL Endpoint:**
- ✅ Real API calls for Cook County, IL
- ✅ Real API calls for Denver County, CO
- ✅ All Standard IL percentage levels (30%, 50%, 80%)
- ✅ Different household sizes (1, 2, 4, 8)
- ✅ Caching with real API responses
- ✅ Historical year data (2024, 2025)
- ✅ Comparison between MTSP and Standard IL results

**Error Handling (Both Endpoints):**
- ✅ Invalid state code error handling (MTSP & Standard IL)
- ✅ Invalid county error handling (MTSP & Standard IL)

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
