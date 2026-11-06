# MyFriendBen

[MyFriendBen](myfriendben.org) was created by [Gary Community Ventures](https://garycommunity.org/), a Denver-based organization. We co-designed MyFriendBen with a group of Colorado families who are participating in a direct cash assistance program. Families told us it was difficult and time-consuming to know what benefits they were entitled to. We are defining “benefits” as public benefits (includes city, county, state and federal), tax credits, financial assistance, nonprofit supports and services. MyFriendBen only includes benefits and tax credits with an annual value of at least $300 or more a year.

Taking inspiration from AccessNYC, and connecting with [PolicyEngine's](https://github.com/PolicyEngine/policyengine-us) API for benefits calculation, we built out a universal benefits screener with the goal to increase benefit participation rates by making key information - like dollar value and time to apply - more transparent, accessible, and accurate. The platform is currently live in Colorado and has been tested with over 40 benefits.

This is the repository for the backend Python/Django rules engine that takes household demographic data and returns benefits eligibility and estimated values. The frontend repository can be accessed [here](https://github.com/Gary-Community-Ventures/benefits-calculator).

## Set Up Benefits-API (back-end part)

Setup instructions are located in the [Wiki](https://github.com/Gary-Community-Ventures/benefits-api/wiki/Get-Started).

### Pre-commit hook

A pre-commit hook runs [black](https://black.readthedocs.io/) on staged Python files, so formatting
problems surface before CI rejects the PR. With a Python 3.11+ virtualenv at `venv/` (`.python-version`
pins 3.12), run once per clone:

```bash
make setup
```

This installs `requirements-dev.txt` and runs `pre-commit install`. If black reformats a file, the
commit stops; `git add` the changes and commit again. To check every file: `venv/bin/pre-commit run --all-files`.

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

## Redis in local development

Set `REDIS_URL` in your `.env` to a loopback address (e.g.
`redis://127.0.0.1:6379/0`) and `manage.py runserver` will auto-start a
small, local `redis-server` so your development environment mirrors
Heroku's cache behavior. Leaving `REDIS_URL` unset is still the default and
gives you an in-memory cache — nothing is started and nothing is required.

What it starts: a 25 MB `redis-server` with `allkeys-lru` eviction and no
persistence (no AOF, no RDB saves), bound to loopback only. On Linux/macOS it
looks for `redis-server` on `PATH`; on Windows it tries a native binary
(Memurai or a native `redis-server.exe` build) first and falls back to WSL if
available.

It only engages when `DEBUG = True`, `REDIS_URL` targets loopback, and
nothing is already listening on that port — if Redis is already running
(locally installed, a system service, etc.) it's left alone.

It keeps running after you stop the dev server with Ctrl-C (daemonized on
Linux/macOS, detached into its own process group on Windows), so repeated
`runserver` restarts don't spawn duplicate instances. Stop it with:

```sh
redis-cli -p <port> shutdown
# or, when Redis was started inside WSL:
wsl -- redis-cli -p <port> shutdown
```

Opt out per invocation with `--no-redis`, or persistently by setting
`AUTO_START_REDIS=false` in your `.env` or shell environment.
