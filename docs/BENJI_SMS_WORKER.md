# Benji SMS worker and broker

The background worker that answers Benji texts (MFB-2436; design: MFB-1916 proposal v3,
decision 5). The inbound webhook acknowledges Twilio straight away and queues the turn,
and the worker generates and sends the reply. This document covers the infrastructure:
the broker, the worker process, the dead-letter path and the alarms. The turn itself
lands in MFB-2440.

## What runs where

| Piece | Where |
| --- | --- |
| Celery app | `benefits/celery.py`, settings in the `CELERY_*` block of `benefits/settings.py` |
| Broker wiring (TLS, timeouts, queue keys) | `benefits/celery_config.py` |
| Jobs, retry policy, dead-letter hook, `enqueue_turn` | `screener/tasks.py` |
| Dead-letter rows | `BenjiSmsDeadLetter` (`screener/models.py`), read-only in the admin for superusers |
| Worker process type | `worker` in the `Procfile` |
| Broker alarms | `manage.py check_benji_sms_broker`, run by Heroku Scheduler |
| End-to-end check | `manage.py benji_sms_worker_check [--fail]` |

**One queue, one job.** Everything runs on the `benji_sms` queue. `screener.benji_sms_turn`
is the job. `screener.benji_sms_ping` is a probe that runs under the same policy so the
check proves the path a turn takes.

**Payloads carry ids only:** the conversation id and the inbound Twilio `MessageSid`.
Never message text, the phone number or its hash. `enqueue_turn` refuses anything else.

**At least once.** Jobs are acknowledged after they run, so a turn can run twice and has
to absorb that (MFB-2440: the SID goes to ai-service as `client_message_id`). A job comes
back to the queue when its worker stops mid-job:
- On a Heroku restart (deploys, the daily cycle, config changes), Heroku sends SIGTERM to
  every process in the dyno. The Procfile sets `REMAP_SIGTERM=SIGQUIT`, so the pool
  children ignore it and the worker runs a cold shutdown. It gives running jobs 25 s to
  finish (`CELERY_WORKER_SOFT_SHUTDOWN_TIMEOUT`, inside Heroku's 30 s), then hands the
  rest back to the broker for the next worker.
- If a pool child dies mid-job, the job is requeued at once.
- If the whole worker vanishes without handing jobs back (SIGKILL, a crash), they return
  after the 300 s visibility timeout.

Each job is delivered at most 3 times: its two attempts, plus one redelivery after a lost
worker. The count is kept on the broker. A job past the cap is dead-lettered without
running (`TooManyDeliveries`), so one that kills its worker every time cannot loop.

**Retries.** Connection errors, timeouts and `TransientTurnError` get one retry, 5 s
later. Any other error fails at once. Each attempt has an 80 s soft limit and a 95 s hard
limit. That allows one ai-service call of at most 35 s (`AI_SERVICE_WORKER_TIMEOUT`) and up
to three Twilio calls of 10 s each. The worst case for a turn that fails both attempts is
therefore about three minutes. The proposal's 60 s was a working figure for a successful
turn.

**Sentry and logs.** Installing Celery switches on Sentry's Celery integration. It
attaches each job's arguments and stack locals to its events, which for a turn means the
SID and, once MFB-2440 lands, the number and the message text. `benefits/sentry_scrub.py`
strips both from every Celery event. It also replaces anything shaped like a MessageSid in
any event, because SIDs surface elsewhere too: Celery's "Task ... received" breadcrumbs, a
Twilio request URL, a Twilio error's text. The turn task masks the SID in Celery's own
log lines (`argsrepr`), retries included, so the worker's Heroku logs show
`<MessageSid>` instead.

## The broker is not the cache

The broker is its own Heroku Redis add-on, attached as `CELERY_BROKER`, so its URL
arrives as `CELERY_BROKER_URL`. It runs `maxmemory-policy noeviction`. Nothing falls
back to `REDIS_URL`. The cache Redis is 25 MB, shared with every cache in the app, and
wrapped in `IGNORE_EXCEPTIONS`, so an outage looks like a cache miss. A queue on it
would lose jobs silently.

With no `CELERY_BROKER_URL` and eager mode off, `enqueue_turn` and the worker check
raise `BrokerNotConfigured`. Without that check, Celery would try an AMQP broker on
localhost and fail with a connection-refused error that does not name the missing
setting.

## Local development

Nothing to set up. `CELERY_TASK_ALWAYS_EAGER` defaults to `DEBUG`, so a job runs in the
process that queues it, and tests run eager too (`pytest.ini`). Eager jobs behave as
they would on a worker: retried, then dead-lettered, with the failure on the result
rather than raised (`CELERY_TASK_EAGER_PROPAGATES` is off).

To run a real worker against a local Redis, use a database the cache and the tests do
not use:

```bash
export CELERY_BROKER_URL=redis://127.0.0.1:6379/9 CELERY_TASK_ALWAYS_EAGER=False
```

```bash
FORKED_BY_MULTIPROCESSING=1 celery --app benefits worker --queues benji_sms --concurrency 2 --loglevel INFO
```

`FORKED_BY_MULTIPROCESSING=1` is for macOS only. billiard starts pool children by spawn
there, and without it every job fails with `not enough values to unpack (expected 3,
got 0)`. Heroku runs Linux, where the children fork, so production does not need it.
`--pool solo` also works.

`REMAP_SIGTERM` is not needed locally; Ctrl+C is a warm shutdown. Then, in another shell
with the same two variables:

```bash
python manage.py benji_sms_worker_check
```

```bash
python manage.py benji_sms_worker_check --fail
```

## Provisioning (staging first, then production)

Steps 1 to 4 are one-time and per app. Replace `<app>` with the Heroku app name.

1. **Broker add-on.** Two things decide the plan: durability and connections.
   - **Durability.** Heroku Redis Mini keeps no data across a reboot or failure and has
     no standby. If the instance restarts, every queued job and every job handed out but
     not yet acknowledged is lost, with no dead-letter row and no alarm (the depth check
     reads 0 afterwards). Premium plans keep an append-only file and have an HA standby.
     Mini is fine for staging. Production needs a decision before MFB-2447 scales the
     worker up: premium-0, or Mini with that loss accepted and written down.
   - **Connections.** The queue needs almost nothing: a job is a few hundred bytes. Each
     web process holds up to 4 broker connections once it has published
     (`BROKER_POOL_LIMIT`). The worker holds a few for its main process and each of its
     2 children, one of them per child for the delivery count. Each Scheduler run and
     one-off dyno opens 1. Mini allows 20 in total, so if
     (web dynos × `WEB_CONCURRENCY` × 4) + 8 is over 20, take a larger plan. Raising the
     worker's concurrency adds about 2 per child. If the broker runs out of connections,
     the delivery count fails open: jobs still run, but uncounted.

   ```bash
   heroku addons:create heroku-redis:mini --as CELERY_BROKER -a <staging-app>
   ```

   ```bash
   heroku addons:create heroku-redis:premium-0 --as CELERY_BROKER -a cobenefits-api
   ```

   ```bash
   heroku redis:maxmemory CELERY_BROKER --policy noeviction -a <app>
   ```

2. **Preboot on the web dynos**, so a deploy never leaves the webhook unreachable.

   ```bash
   heroku features:enable preboot -a <app>
   ```

3. **Scheduler job for the alarms.** Add the Scheduler add-on if the app has none. Then,
   in its dashboard, run `python manage.py check_benji_sms_broker` every 10 minutes.

   ```bash
   heroku addons:create scheduler:standard -a <app>
   ```

4. **Sentry alert rules.** Alarms are ERROR logs, so they arrive as Sentry issues. Sentry
   groups events by message template. Each broker alarm kind (memory, depth, policy,
   unreachable, unconfigured) is its own issue, and every dead letter joins one issue.
   An alert on "a new issue is created" would therefore fire once and then go quiet.
   Instead, alert when an issue is seen more than 0 times in 15 minutes (with a
   threshold of 0, any interval Sentry offers works), and also when an issue changes
   from resolved to unresolved. Use a 10-minute action interval. Set up three rules:
   - logger `screener.management.commands.check_benji_sms_broker` (broker alarms)
   - logger `screener.tasks`, level error. This catches both `Benji SMS job
     dead-lettered` and `... could not be dead-lettered`, the case where the dead-letter
     row itself failed to write. Those are the only ERROR lines that logger writes.
   - logger `celery.worker.request` with the message containing `Hard time limit`: a
     job killed at 95 s, which writes no row.

   Staging and production both report to Sentry as `production` unless told otherwise.
   Set `SENTRY_ENVIRONMENT=staging` on the staging app and filter each rule by
   environment, so the staging test does not page for production.

   ```bash
   heroku config:set SENTRY_ENVIRONMENT=staging -a <staging-app>
   ```

5. **Deploy.** Migrations 0173 and 0174 apply in the usual migration step.

## Verifying on staging

```bash
heroku ps:scale worker=1 -a <staging-app>
```

```bash
heroku run python manage.py benji_sms_worker_check -a <staging-app>
```

```bash
heroku run python manage.py benji_sms_worker_check --fail -a <staging-app>
```

The first prints `Round trip OK`. The second prints `Forced failure dead-lettered after
2 attempt(s)`, and the row appears under Benji SMS dead letters in the admin. It fails if
the row records any other number of attempts, since that would mean the retry never ran.
Fire both alarms on purpose and confirm each reaches Sentry as its own issue:

```bash
heroku run python manage.py check_benji_sms_broker --memory-threshold 0 --depth-threshold 0 -a <staging-app>
```

Delete the ping's dead-letter row from a shell afterwards. The admin is read-only.

## Production

A new process type starts at zero dynos. After the production deploy, confirm that
`heroku ps` shows the worker at zero (or not at all), and leave it there until MFB-2447
scales it up at launch.

```bash
heroku ps -a cobenefits-api
```

While the worker is at zero, a job queued in production waits on the broker, and the
depth alarm fires once 25 are waiting. Nothing queues a turn until the inbound webhook
(MFB-2439) exists and the `benji_sms` flag is on.

## Dead letters

A row means a job failed for good. That is one of three things:
- it failed every attempt;
- its retry could not be queued (a full or unreachable broker). Celery would otherwise
  delete it silently;
- it was delivered more than 3 times (`TooManyDeliveries`).

A row holds the task name and id, the conversation, the inbound SID, the attempt count and
the class of the last error, never its message.
Writing the row logs `Benji SMS job dead-lettered` at ERROR, which is the alarm. Rows
cascade with their conversation, in the ORM and in the database (migration 0174), so a
deletion request removes them too. If the conversation was already gone, the row keeps
neither the conversation nor the SID.

Three failures leave no row:
- **A job killed by the 95 s hard time limit.** Celery skips the failure hook then and logs
  `Hard time limit (95s) exceeded for screener.benji_sms_turn[<task id>]` at ERROR, which
  reaches Sentry. The 80 s soft limit normally ends the job first, through the hook, so it
  is dead-lettered.
- **The row itself failed to write** (for example, the database was unavailable). This is
  logged as `Benji SMS job <task id> (<task>) failed every attempt and could not be
  dead-lettered` at ERROR.
- **A job lost with a non-persistent broker** (see Provisioning, step 1).
