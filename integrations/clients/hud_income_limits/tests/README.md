# HUD Income Limits Client Tests

This directory contains tests for the HUD Income Limits API client.

## Test Files

### `test_client.py` - Unit Tests (Mocked)
Unit tests that mock all external API calls. These tests:
- Run fast (no network calls)
- Don't require HUD API credentials
- Test client logic, error handling, and edge cases
- Should always pass in CI/CD

### `test_integration.py` - Integration Tests (VCR Cassettes)
Integration tests that verify HUD API behavior. These tests:
- **Default**: Use VCR cassettes (fast, no API token needed)
- **CI (PRs)**: Replay cassettes only
- **CI (push to main)**: Make real API calls to validate integrations
- **Local with token**: Can record new/update cassettes

See **[docs/TESTING.md](../../../docs/TESTING.md)** for complete VCR documentation.

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

1. **Install dependencies:** `pip install -r requirements.txt`
2. **Set Django settings:** `export DJANGO_SETTINGS_MODULE=benefits.settings`
3. **For recording cassettes** (optional): Add `HUD_API_TOKEN=your_token` to `.env`

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

**Run only integration tests (uses VCR cassettes):**
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
| `-m "not integration"` | Fast (~1s) | No | Development, quick validation |
| `-m integration` | Fast (~1s) | No (uses cassettes) | Full validation |
| All tests | Fast (~2s) | No | Complete validation |

## CI/CD Configuration

Integration tests automatically use VCR cassettes in CI. See **[docs/TESTING.md](../../../docs/TESTING.md)** for complete CI/CD strategy.

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

**Integration tests failing:**
- Should work without API token (uses VCR cassettes)
- If cassettes missing: Add `HUD_API_TOKEN=your_token` to `.env` to record them
- Get token at: https://www.huduser.gov/hudapi/public/register
- See **[docs/TESTING.md](../../../docs/TESTING.md)** for VCR troubleshooting

**"DJANGO_SETTINGS_MODULE not set":**
- Run: `export DJANGO_SETTINGS_MODULE=benefits.settings`
- OR add to your shell config (`~/.bashrc` or `~/.zshrc`)

**Cache-related test failures:**
- Tests clear cache in `setUp()` to avoid interference
- If issues persist, manually clear Django cache
- Try running with `--cache-clear` flag
