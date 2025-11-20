# Testing Guide

## Overview

Our test suite includes unit tests and integration tests. Integration tests use **VCR (Video Cassette Recorder)** to record and replay HTTP interactions, making them fast and deterministic while still validating real API behavior.

---

## Running Tests

### All Tests
```bash
# Run all tests (unit + integration with VCR cassettes)
pytest

# With coverage
pytest --cov --cov-report=html
```

### Unit Tests Only
```bash
# Skip integration tests
pytest -m "not integration"
```

### Integration Tests Only
```bash
# Run only integration tests (uses VCR cassettes)
pytest -m integration
```

---

## Integration Tests with VCR

### How It Works

**VCR (Video Cassette Recorder)** records HTTP requests/responses to YAML files called "cassettes". Once recorded, tests replay these cassettes instead of making real API calls.

**Benefits**:
- ⚡ **Fast**: No network latency, tests run in milliseconds
- 🔒 **Secure**: Automatically scrubs API keys and sensitive data
- 📦 **Deterministic**: Same inputs always produce same outputs
- 🌐 **Offline**: Tests work without internet or API credentials
- ✅ **Real**: Based on actual API responses, catches schema changes

### Test Behavior by Environment

Controlled by the `VCR_MODE` environment variable:

| Environment | VCR_MODE | Behavior | API Calls |
|------------|----------|----------|-----------|
| **PRs** | `none` | Uses existing cassettes only | ❌ No |
| **Push to main** | `new_episodes` | Makes real API calls, updates cassettes | ✅ Yes |
| **Local (default)** | `once` | Uses cassettes, records if missing | Only if cassette missing |
| **Force re-record** | `all` | Re-records all cassettes | ✅ Yes (overwrites) |

### Running Integration Tests Locally

#### Default: Use Existing Cassettes
```bash
# Uses VCR cassettes (fast, no credentials needed)
pytest -m integration
```

#### Record New Cassettes
```bash
# If you have HUD_API_TOKEN set, missing cassettes will be recorded
export HUD_API_TOKEN=your_token_here
pytest -m integration
```

#### Force Re-record All Cassettes
```bash
# Useful when API responses change
export HUD_API_TOKEN=your_token_here
VCR_MODE=all pytest -m integration
```

#### Run Specific Test
```bash
# Test a specific integration
pytest integrations/clients/hud_income_limits/tests/test_integration.py::TestHudIntegrationMTSP::test_real_api_call_cook_county_il -v
```

---

## Cassette Management

### Cassette Storage

Cassettes are stored in `cassettes/` directories next to test files:
```
integrations/clients/hud_income_limits/tests/
├── test_integration.py
└── cassettes/
    ├── test_real_api_call_cook_county_il.yaml
    ├── test_real_api_call_denver_county_co.yaml
    └── ...
```

### When to Update Cassettes

Update cassettes when:
- ✅ API endpoints change
- ✅ Response schemas are updated
- ✅ You add new test cases
- ✅ API behavior changes (e.g., new validation rules)

**How to update**:
```bash
export HUD_API_TOKEN=your_token_here
VCR_MODE=all pytest -m integration
git add integrations/**/cassettes/*.yaml
git commit -m "Update VCR cassettes for API changes"
```

### Cassette Security

VCR automatically scrubs sensitive data:
- ✅ API keys and tokens
- ✅ Authorization headers
- ✅ Email addresses and PII
- ✅ IP addresses
- ✅ Internal file paths

**Always review cassettes before committing**:
```bash
git diff integrations/**/cassettes/*.yaml
```

---

## CI/CD Testing Strategy

### Pull Requests (VCR_MODE=none)
```yaml
- Uses VCR cassettes only
- No real API calls
- Fast feedback (~30 seconds)
- No API credentials needed
```

**If cassettes are missing**: Test will fail, prompting you to record them locally.

### Push to Main (VCR_MODE=new_episodes)
```yaml
- Makes real API calls
- Updates cassettes with new data
- Validates actual API integrations
- Requires HUD_API_TOKEN secret
```

**Purpose**: Catch API breaking changes before production deployment.

---

## Writing New Integration Tests

### Basic Pattern

```python
import pytest
from django.test import TestCase

@pytest.mark.integration  # This enables VCR automatically
class TestYourIntegration(TestCase):
    """Integration tests for your API client."""

    @classmethod
    def setUpClass(cls):
        """Set up test class."""
        super().setUpClass()
        # Check if we're using real API calls (VCR_MODE is "new_episodes" or "all")
        vcr_mode = os.getenv("VCR_MODE", "once").lower()
        cls.using_real_api = vcr_mode in ["new_episodes", "all"]
        cls.has_token = config("YOUR_API_TOKEN", default=None) is not None

    def setUp(self):
        """Set up test data."""
        # Skip if real API calls needed but no token
        if self.using_real_api and not self.has_token:
            pytest.skip("Real API call requested but YOUR_API_TOKEN not set")

        # Set up test data
        self.test_data = ...

    def test_your_api_call(self):
        """Test your API integration."""
        # Make API call (VCR will handle recording/playback)
        result = your_client.call_api(...)

        # Assert expected behavior
        self.assertEqual(result, expected)
```

### Key Points

1. **Use `@pytest.mark.integration`**: Enables VCR automatically
2. **Check for tokens in `setUp()`**: Skip gracefully when token missing
3. **Write descriptive test names**: Cassette files use test names
4. **Test both success and error cases**: Record error responses too
5. **Use realistic test data**: Helps catch real-world issues

---

## Troubleshooting

### "Cassette not found" error in CI

**Problem**: Test tries to make real API call but cassette doesn't exist.

**Solution**:
```bash
# Locally, record the missing cassette
export HUD_API_TOKEN=your_token_here
pytest -m integration -k test_name_that_failed
git add integrations/**/cassettes/*.yaml
git commit -m "Add missing VCR cassette"
git push
```

### Tests pass locally but fail in CI

**Possible causes**:
1. **Cassettes not committed**: Check `git status`
2. **Different test data**: Ensure test data is deterministic
3. **Time-dependent tests**: Mock time.time() or dates

### API responses changed

**Symptoms**: Tests pass with cassettes but fail with real API calls.

**Solution**:
```bash
# Re-record cassettes with updated API responses
export HUD_API_TOKEN=your_token_here
VCR_MODE=all pytest -m integration
git add integrations/**/cassettes/*.yaml
git commit -m "Update cassettes for API changes"
```

### Need to test against real API

```bash
# Force re-record mode for debugging
VCR_MODE=all pytest -m integration -v
```

---

## Best Practices

### ✅ DO

- **Commit cassettes** to version control
- **Review cassette diffs** before committing
- **Use descriptive test names** (they become cassette filenames)
- **Test error cases** (record error responses in cassettes)
- **Update cassettes** when APIs change
- **Run integration tests** before opening PRs

### ❌ DON'T

- **Commit real API keys** (VCR scrubs them, but double-check)
- **Edit cassettes manually** (regenerate them instead)
- **Skip integration tests** without good reason
- **Ignore cassette update warnings** in PR reviews
- **Mock external APIs** in integration tests (use VCR instead)

---

## GitHub Secrets Required

For CI to run integration tests with real API calls (push to main):

```bash
# Add to GitHub repository secrets
gh secret set HUD_API_TOKEN --body "your_hud_api_token"
```

Verify secrets are set:
```bash
gh secret list
```

---

## Additional Resources

- [VCR.py Documentation](https://vcrpy.readthedocs.io/)
- [Pytest Integration Documentation](https://docs.pytest.org/en/stable/example/markers.html)
- [Django Testing Best Practices](https://docs.djangoproject.com/en/stable/topics/testing/overview/)

---

## Quick Reference

| Task | Command |
|------|---------|
| Run all tests | `pytest` |
| Run unit tests only | `pytest -m "not integration"` |
| Run integration tests | `pytest -m integration` |
| Record new cassettes | `HUD_API_TOKEN=token pytest -m integration` |
| Force re-record all | `HUD_API_TOKEN=token VCR_MODE=all pytest -m integration` |
| Run with coverage | `pytest --cov --cov-report=html` |
| Run specific test | `pytest path/to/test.py::TestClass::test_method` |
| View coverage report | `open htmlcov/index.html` |
