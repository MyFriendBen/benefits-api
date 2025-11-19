# VCR Cassettes for HUD Income Limits Integration Tests

This directory contains VCR cassette files that record HTTP interactions with the HUD API.

**All sensitive information is automatically scrubbed** from these cassettes before being saved.

## 📚 Full Documentation

For complete information about integration testing and VCR cassettes, see:

**[docs/INTEGRATION_TESTING.md](../../../../docs/INTEGRATION_TESTING.md)**

## Quick Reference

### Recording New Cassettes

```bash
# 1. Add HUD_API_TOKEN to your .env
# 2. Run the test
pytest -m integration integrations/clients/hud_income_limits/tests/test_integration.py

# 3. Review cassette for REDACTED values
grep -i "authorization" cassettes/*.yaml

# 4. Commit if safe
git add cassettes/*.yaml
```

### Cassettes Are Safe to Commit ✅

- Authorization headers → `REDACTED`
- API keys → `REDACTED`
- Tokens → `REDACTED`
- Credentials → `REDACTED`
