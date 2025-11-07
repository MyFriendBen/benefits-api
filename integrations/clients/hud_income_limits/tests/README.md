# HUD Income Limits Client Tests

This directory contains tests for the HUD Income Limits API client.

## Test Files

### `test_client.py` - Unit Tests (Mocked)
Unit tests that mock all external API calls. These tests:
- Run fast (no network calls)
- Don't require HUD API credentials
- Test client logic, error handling, and edge cases
- Should always pass in CI/CD

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

## Running Tests

### Prerequisites

1. **Install test dependencies:**
   ```bash
   pip install pytest pytest-django pytest-cov
   # OR install all project dependencies:
   pip install -r requirements.txt
   ```

2. **Set Django settings:**
   ```bash
   export DJANGO_SETTINGS_MODULE=benefits.settings
   ```

3. **For integration tests only** - Add HUD API token to `.env`:
   ```bash
   HUD_API_TOKEN=your_token_here
   ```

### Running Tests

**Note:** If `pytest` command not found, use `python -m pytest` or `python3 -m pytest` instead.

**Run all tests (unit + integration):**
```bash
python -m pytest integrations/clients/hud_income_limits/tests/ -v
```

**Run only unit tests (fast, no API token required):**
```bash
# By file:
python -m pytest integrations/clients/hud_income_limits/tests/test_client.py -v

# By marker:
python -m pytest -m "not integration" integrations/clients/hud_income_limits/tests/ -v
```

**Run only integration tests (requires HUD_API_TOKEN in .env):**
```bash
python -m pytest -m integration integrations/clients/hud_income_limits/tests/ -v
```

**Run specific test:**
```bash
# Run one test method:
python -m pytest integrations/clients/hud_income_limits/tests/test_client.py::TestHudIncomeClientMTSP::test_get_screen_mtsp_ami_80_percent_success -v

# Run one test class:
python -m pytest integrations/clients/hud_income_limits/tests/test_client.py::TestHudIncomeClientMTSP -v
```

**Run with coverage report:**
```bash
python -m pytest --cov=integrations.clients.hud_income_limits integrations/clients/hud_income_limits/tests/ -v
```

**Run with verbose output and show print statements:**
```bash
python -m pytest integrations/clients/hud_income_limits/tests/ -vv -s
```

### Test Execution Summary

| Command | Speed | Requires API Token | Use Case |
|---------|-------|-------------------|----------|
| `-m "not integration"` | Fast (~1s) | No | Development, CI/CD |
| `-m integration` | Slow (~15s) | Yes | Pre-deployment verification |
| All tests | Medium (~15s) | Yes | Complete validation |

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

**"pytest: command not found":**
- Use `python -m pytest` or `python3 -m pytest` instead
- OR install pytest in your environment: `pip install pytest pytest-django`
- OR add pytest to PATH: `export PATH="$HOME/.pyenv/shims:$PATH"`

**"No module named pytest":**
- Install test dependencies: `pip install pytest pytest-django pytest-cov`
- OR install all project dependencies: `pip install -r requirements.txt`
- Make sure you're in your virtual environment (if using one)

**"python: command not found" (but python3 works):**
- Use `python3 -m pytest` for all commands
- OR set python3 as default with pyenv: `pyenv global 3.10.18`
- OR create alias in `~/.zshrc`: `alias python=python3`

**Integration tests failing with "HUD_API_TOKEN not set":**
- Add `HUD_API_TOKEN=your_token` to `.env` file in project root
- Get token at: https://www.huduser.gov/hudapi/public/register
- Register for both FMR and Income Limits datasets

**Integration tests timing out:**
- Check internet connection
- Verify HUD API is accessible: `curl https://www.huduser.gov/hudapi/public/`
- Check token has correct dataset permissions (FMR + Income Limits)

**"DJANGO_SETTINGS_MODULE not set":**
- Run: `export DJANGO_SETTINGS_MODULE=benefits.settings`
- OR add to your shell config (`~/.bashrc` or `~/.zshrc`)

**Cache-related test failures:**
- Tests clear cache in `setUp()` to avoid interference
- If issues persist, manually clear Django cache
- Try running with `--cache-clear` flag
