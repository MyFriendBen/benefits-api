# MyFriendBen

[MyFriendBen](myfriendben.org) was created by [Gary Community Ventures](https://garycommunity.org/), a Denver-based organization. We co-designed MyFriendBen with a group of Colorado families who are participating in a direct cash assistance program. Families told us it was difficult and time-consuming to know what benefits they were entitled to. We are defining “benefits” as public benefits (includes city, county, state and federal), tax credits, financial assistance, nonprofit supports and services. MyFriendBen only includes benefits and tax credits with an annual value of at least $300 or more a year.

Taking inspiration from AccessNYC, and connecting with [PolicyEngine's](https://github.com/PolicyEngine/policyengine-us) API for benefits calculation, we built out a universal benefits screener with the goal to increase benefit participation rates by making key information - like dollar value and time to apply - more transparent, accessible, and accurate. The platform is currently live in Colorado and has been tested with over 40 benefits.

This is the repository for the backend Python/Django rules engine that takes household demographic data and returns benefits eligibility and estimated values. The frontend repository can be accessed [here](https://github.com/Gary-Community-Ventures/benefits-calculator).

## Set Up Benefits-API (back-end part)

Setup instructions are located in the [Wiki](https://github.com/Gary-Community-Ventures/benefits-api/wiki/Get-Started).

## Testing

We use pytest for testing with two types of tests:

- **Unit tests**: Fast, mocked tests that don't require external services
- **Integration tests**: Tests that verify integration with real external APIs using VCR

### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests (skip integration tests)
pytest -m "not integration"

# Run only integration tests
pytest -m integration
```

For detailed information about writing and maintaining integration tests, see [docs/INTEGRATION_TESTING.md](docs/INTEGRATION_TESTING.md).

## Benbot AI assistant

Benbot is an AI assistant on the results page. The browser calls **this API**,
which enforces the feature flag, assembles the screen context, and proxies to
the standalone **mfb-ai-service**. The browser never calls mfb-ai-service directly.

```
benefits-calculator  ──▶  benefits-api (proxy)  ──▶  mfb-ai-service
   chat widget              screener/assistant.py        FastAPI + Fireworks
```

### Feature flag

Benbot is gated by the `benbot` feature flag (defined in
`screener/feature_flags.py`, `scope="both"`), **off by default**.

1. The flag is registered in code; sync it to all white labels:
   ```bash
   python manage.py sync_feature_flags --dry-run   # preview
   python manage.py sync_feature_flags             # apply
   ```
2. Turn it on per white label in **Admin → General Settings → Feature Flags**.

The proxy views (`screener/assistant.py`) reject requests with
`403 assistant_disabled` when the flag is off, so the flag is real access
control, not just hidden UI.

### Endpoints

- `POST /screens/<screen_uuid>/assistant/conversations/` — open/resume a conversation
- `POST /screens/<screen_uuid>/assistant/conversations/<conversation_id>/messages/` — send a message

### Environment variables

- `AI_SERVICE_URL` — base URL of mfb-ai-service (default `http://localhost:8080`)
- `AI_SERVICE_TOKEN` — shared bearer token; must match the service's `SERVICE_AUTH_TOKEN`. Leave blank for local dev.

### Local dev

Run mfb-ai-service on `:8080` in stub mode (no AI key needed), leave the tokens
blank on both sides, point `AI_SERVICE_URL` at it, and enable the `benbot` flag
for your local white label to exercise the full chain.
