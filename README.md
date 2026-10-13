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

## Redis in local development

When `REDIS_URL` is set and points at a loopback address (localhost / 127.0.0.1)
and Django is running with `DEBUG = True`, `manage.py runserver` will attempt
to auto-start a small, local `redis-server` so the development environment
better mirrors Heroku's cache behavior.

High level rules

- Attempt is only made in the parent process (the autoreloader spawns a child
   process; the start happens only once).
- Requires `DEBUG = True` and a `REDIS_URL` that targets a loopback address.
- If something already listens on the configured Redis port, `runserver` will
   leave it alone and not try to spawn another server.
- You can opt out per invocation with `--no-redis` or persistently with the
   environment variable `AUTO_START_REDIS=false`.

Platform notes

- Linux / macOS: the command looks for `redis-server` on `PATH` and starts it
   with Heroku-like flags (25 MB maxmemory, `allkeys-lru`, no AOF, no saves)
   and `--daemonize yes` so it survives Ctrl-C of the dev server.
- Windows: we try to detect a native Redis-compatible binary first (common
   Windows service: Memurai / `memurai.exe`). If no native binary is found and
   the `wsl` command is available, the command will attempt to start
   `redis-server` inside WSL (this requires `redis-server` to be installed in
   your default WSL distro). WSL startup is used as a fallback so Windows
   developers who run Redis in WSL get the same auto-start convenience.

Notes about missing binaries and side effects

- If no suitable binary is found (native or WSL) `runserver` will print a
   single-line hint and continue without starting Redis. The Django cache
   backend will remain configured to use Redis (i.e. cache misses will behave
   according to your `django_redis` options such as `IGNORE_EXCEPTIONS=True`).
- The WSL fallback depends on `wsl` being on your PATH and a working `redis-`
   server inside your WSL distro. If either is missing, auto-start will be
   skipped and a hint will be shown.

Temporary persistence and git

- The helper creates a temporary directory for Redis persistence files. We
   ignore Redis dump files in the repo; see `.gitignore` for `*.rdb`.

Console messages developers will see

The implementation emits short, human-friendly messages so it's clear what
happened. Examples (angle-bracket tokens are replaced by the actual values):

- When a listener is already present on the target port:

   Redis already listening on <host>:<port>; skipping auto-start.

- When `redis-server` (or Memurai) is found and started natively:

   Starting local redis-server using '<binary>' on port <port> (daemonized).
   To stop: redis-cli -p <port> shutdown

- When no native binary is found but WSL is used to start Redis:

   Starting local redis-server inside WSL (via 'wsl') on port <port> (daemonized).
   To stop: wsl -- redis-cli -p <port> shutdown

- When no binary is found at all:

   redis-server not found on PATH; to enable auto-start install Redis (or
   Memurai on Windows), or set AUTO_START_REDIS=false or use --no-redis; continuing without starting Redis.

Behavior when auto-start is skipped

- If `DEBUG` is False or `REDIS_URL` does not point at loopback, no auto-
   start will be attempted. In those cases `runserver` continues as normal and
   typically does not emit additional messages about Redis.

Stopping the helper Redis instance

You can stop the locally-started Redis the same way you would any Redis
instance:

```sh
redis-cli -p <port> shutdown
# or, when Redis was started inside WSL:
wsl -- redis-cli -p <port> shutdown
```

If you prefer to manage Redis yourself (via your package manager, systemd,
Memurai service on Windows, or `brew services start redis`), `runserver` will
detect the running service and not spawn a second instance.

Production safety

This behavior only runs when `DEBUG = True` and when `REDIS_URL` targets
loopback; it does not affect production deployments. If you want an extra
guard against accidental starts in PaaS environments, a further check such
as refusing to auto-start when `DYNO` (Heroku) is present can be added.
