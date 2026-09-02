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

The suite runs in parallel by default (`-n auto` in `pytest.ini`), which takes it from
roughly three minutes to under one. Two things follow from that:

- **Recording drops back to one process automatically.** `VCR_MODE=all`,
  `VCR_MODE=new_episodes`, and any run with `PE_RECORD=1` may write cassettes, and
  parallel workers would issue duplicate live API calls and race to write the same file.
  `conftest.py` detects these and disables the fan-out, so the recording commands below
  need no extra flags. (`once` — the default when `VCR_MODE` is unset — only writes when
  a whole cassette file is absent, so it keeps the fan-out.)
- **Each worker gets its own Redis database** (1-15) when `REDIS_URL` is set, because
  `clear_cache` issues FLUSHDB and would otherwise wipe other workers' entries mid-test.
  Database 0 is left to serial runs and to `benefits/tests/test_redis_backend.py`.
  `pytest.ini` therefore caps the fan-out with `--maxprocesses 15`, which is what keeps
  `-n auto` safe on a large machine: it counts *logical* cores here (xdist prefers
  physical via `psutil`, which is not installed). Raising the cap past 15 fails with a
  message naming the limit rather than letting workers share a database.

Pass `-n 0` to force a serial run when debugging test interdependence.

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
| **PRs** (`pr-validation`) | `none` | **Read-only:** Replays only. A request with no matching cassette fails the build rather than being recorded live, so a PR cannot pass by reaching a real API. | ❌ No (never records) |
| **Push to main** (`deploy-staging`) | `none` | Same as PRs: replay-only, parallel. Every commit here already passed the PR gate. | ❌ No (never records) |
| **Release** (`deploy-production`) | `all` | **Fresh start:** Never replays. Re-records ALL cassettes from scratch. PolicyEngine spec-scenario tests skip (see below). | ✅ Yes (every non-skipped test hits the live API) |
| **Local (default)** | `once` | **Strict:** Replays existing cassettes. **Errors if test makes new HTTP request not in cassette.** | Only if entire cassette file missing |
| **Strict playback** | `none` | **Read-only:** Replays only. Never records. Errors on any new HTTP requests. | ❌ No (never records) |

Re-recording in CI is never committed — no workflow commits cassettes — so a CI run in `new_episodes` or `all` mode does not refresh what's in the repo. It only changes what that run tests against.

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

## PolicyEngine Spec-Scenario Tests

Every program calculator gets tests that mirror its `spec.md` **Test Scenarios** 1:1 — one test per scenario, asserting eligibility *and* benefit value. Custom (MFB) calculators get plain unit tests, because the rules and amounts are our code. PolicyEngine calculators get the same assertions wrapped as VCR integration tests: the answer comes from PolicyEngine, so we record it once and replay it forever after.

Helpers live in `programs/programs/testing_fixtures/pe_integration.py`; the harness itself is covered by `programs/framework/tests/test_pe_integration_harness.py`. Nothing in the helpers is coupled to `spec.md` — they run a calculator and hand back an `Eligibility`; mirroring Test Scenarios is a convention of the callers.

The harness sits in `framework/` rather than with the PolicyEngine client because it builds `Screen`s and runs calculators. `integrations/clients/policyengine/` is the wire layer only — the POST, the token cache, version resolution — and holds no cassettes.

**A program's own tests and cassettes live next to the program**, not here: `programs/programs/{state}/{program}/tests/` with a `cassettes/` directory beside them. `conftest.py` derives `cassette_library_dir` from each test file's own directory, so a test and its cassettes always travel together.

### Writing one

```python
import pytest
from programs.framework.tests.integration_test_helpers import (
    PeIntegrationTestCase, add_income, add_member, calc_pe_program, make_program, make_screen,
    screener_value,
)

@pytest.mark.integration          # applies VCR (the base class carries this too)
class TestTxHeadStart(PeIntegrationTestCase):
    pe_version = "1.779.3"        # version the cassettes were recorded at

    def test_scenario_1_single_parent_child_age_3_under_income_limit(self):
        screen = make_screen(screen_id=1, white_label_code="tx", state_code="TX",
                             household_size=2, zipcode="78701", county="Travis County")
        parent = add_member(screen, member_id=1, relationship="headOfHousehold", age=34)
        add_income(parent, amount=1_496)
        add_member(screen, member_id=2, relationship="child", age=3)
        program = make_program("tx", "tx_head_start", year="2025")

        eligibility = calc_pe_program(screen, TxHeadStart, program)

        self.assertTrue(eligibility.eligible)
        self.assertEqual(screener_value(eligibility), 12_076)
```

Three rules make a PolicyEngine cassette replayable — the helpers enforce them, don't work around them:

1. **Assign explicit primary keys.** The request keys `household.people` by member id and the *response* is keyed the same way, so a cassette recorded under different auto-increment pks can neither be matched nor read.
2. **Pin the model version** via `pe_version`. Unpinned requests send the floating `current` alias, which makes the recorded body non-reproducible and can fire a second HTTP call (`GET /versions/us`).
3. **Assert the truncated value** with `screener_value(...)`. PolicyEngine returns fractional dollars; the API truncates before serving, so whole dollars are what the spec and the user see.

### Recording and verifying

Run these with `pytest`, **not** `manage.py test` — VCR is a pytest fixture, so under the Django runner these tests would hit PolicyEngine live on every run.

```bash
# 1. Record (needs POLICY_ENGINE_CLIENT_ID / POLICY_ENGINE_CLIENT_SECRET)
PE_RECORD=1 VCR_MODE=once venv/bin/pytest programs/programs/white_labels/mo/pts/tests/ -v

# 2. Prove it replays with no network
VCR_MODE=none venv/bin/pytest programs/programs/white_labels/mo/pts/tests/ -q

# 3. Commit the cassettes with the tests
git add programs/programs/white_labels/mo/pts/tests/
```

`PE_RECORD=1` is what allows the live auth0 token exchange. Without it every run seeds a placeholder token and touches no network, so an ordinary `pytest` never authenticates even on a machine with PolicyEngine credentials in `.env`.

The pinned version must be one PolicyEngine currently serves — it rejects exact versions other than what `current`/`frontier` resolve to:

```bash
curl -s https://household.api.policyengine.org/versions/us
```

### Refreshing after PolicyEngine moves

A cassette is a snapshot of one PolicyEngine version's answer. When we bump the pin, or PolicyEngine promotes a release past it, re-record: update `pe_version`, delete the affected cassettes, re-run step 1, and review the value diff. A changed value is a signal, not a formality — either the spec's expected number needs review or PolicyEngine changed behavior. Update `spec.md` and the assertion together.

Re-recording and adopting a new PolicyEngine version are always the same act: PolicyEngine serves only what `current`/`frontier` currently resolve to, and returns `422 unsupported_version` for anything else. A cassette can never be refreshed at its original pin.

Because of that, these tests **skip under `VCR_MODE=all`** (which never replays and would re-run every scenario against a version PolicyEngine may no longer serve). Live drift detection belongs in a scheduled job that bumps the pin deliberately, not in a deploy.

Anything a *failing* test records is discarded on teardown — the cassette is restored, or removed if the test created it — so a bad recording can't leave an error response behind to replay forever. If a recording attempt fails, fix the cause and re-run. (Note that VCR's own `record_on_exception` cannot do this from inside a fixture: pytest never throws a test failure into a fixture generator, so `Cassette.__exit__` sees a clean exit. `conftest.py` tracks the outcome itself via `pytest_runtest_makereport`.)

---

## Cassette Management

### Cassette Storage

Cassettes are stored in `cassettes/` directories next to test files, named `<TestClass>.<test_name>.yaml`:
```
integrations/clients/hud_income_limits/tests/
├── test_integration.py
└── cassettes/
    ├── TestHudIntegrationMTSP.test_real_api_call_cook_county_il.yaml
    ├── TestHudIntegrationMTSP.test_real_api_call_denver_county_co.yaml
    └── ...
```

The class prefix matters: without it, two identically-named methods in different classes in the same module share one cassette and silently replay each other's recording.

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
- Replays existing cassettes only
- Never records; no API calls, no credentials needed
- A request with no matching cassette fails the build
- Runs in parallel (-n auto)
```

**If new tests added**: record their cassettes locally and commit them. CI will not record
on your behalf — a missing cassette is a build failure, which is the point: it keeps a PR
from passing against a live API.

### Push to Main (VCR_MODE=none)

`deploy-staging` runs the same strict playback as PR validation. Every commit reaching
main has already passed that gate, so there is nothing left to record.

### Release / Production Deploy (VCR_MODE=all)
```yaml
- Re-records ALL cassettes
- Makes real API calls for every test
- Validates actual API integrations
- Ensures API interface hasn't changed
- Requires HUD_API_TOKEN secret
```

**Purpose**: Catch API breaking changes before a production release.

**PolicyEngine spec-scenario tests skip in this mode.** `all` never replays, and these cassettes pin an exact model version that PolicyEngine stops serving as soon as it promotes past it (`422 unsupported_version`) — so re-recording them on a release could only ever fail, and it would make a production deploy depend on live PolicyEngine with no drift report besides. Live PE re-runs belong in a scheduled, non-blocking drift job that bumps the pin deliberately (see MFB-1565). HUD cassettes still re-record here as before.

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
