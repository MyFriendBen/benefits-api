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

**At least once.** Jobs are acknowledged after they run. A job whose worker died is
handed out again after the 300 s visibility timeout, so a turn can run twice and has to
absorb that (MFB-2440: the SID goes to ai-service as `client_message_id`).

**Retries.** Connection errors, timeouts and `TransientTurnError` get one retry, 5 s
later. Any other error fails at once. Each attempt has a 50 s soft limit and a 60 s hard
limit; one ai-service call is at most 35 s (`AI_SERVICE_WORKER_TIMEOUT`). The worst case
for a turn that fails both attempts is therefore about two minutes. The proposal's 60 s
was a working figure for a successful turn.

## The broker is not the cache

The broker is its own Heroku Redis add-on, attached as `CELERY_BROKER`, so its URL
arrives as `CELERY_BROKER_URL`. It runs `maxmemory-policy noeviction`. Nothing falls
back to `REDIS_URL`. The cache Redis is 25 MB, shared with every cache in the app, and
wrapped in `IGNORE_EXCEPTIONS`, so an outage looks like a cache miss. A queue on it
would lose jobs silently.

With no `CELERY_BROKER_URL` and eager mode off, `enqueue_turn` and the worker check
raise `BrokerNotConfigured`. Without that check, Celery would try an AMQP broker on
localhost and the publish would hang.

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

Then, in another shell with the same two variables:

```bash
python manage.py benji_sms_worker_check
```

```bash
python manage.py benji_sms_worker_check --fail
```

## Provisioning (staging first, then production)

Steps 1 to 4 are one-time and per app. Replace `<app>` with the Heroku app name.

1. **Broker add-on.** Size it for the queue and for connections. The queue needs almost
   nothing: a job is a few hundred bytes. Connections are what count. Each web process
   holds up to 4 broker connections once it has published (`BROKER_POOL_LIMIT`). The
   worker holds a few for its main process and each of its 2 children. Each Scheduler
   run and one-off dyno opens 1. Mini allows 20 in total, so if
   (web dynos × `WEB_CONCURRENCY` × 4) + 8 is over 20, take a larger plan.

   ```bash
   heroku addons:create heroku-redis:mini --as CELERY_BROKER -a <app>
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

4. **Sentry alert rules.** Alarms are ERROR logs, so they arrive as Sentry issues.
   Create an alert that notifies on new issues from the logger
   `screener.management.commands.check_benji_sms_broker`, and another on messages
   containing `Benji SMS job dead-lettered` (logger `screener.tasks`).

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
2 attempt(s)`, and the row appears under Benji SMS dead letters in the admin. Fire both
alarms on purpose and confirm each reaches Sentry:

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

A row means a job failed every attempt. It holds the task name and id, the conversation,
the inbound SID, the attempt count and the class of the last error, never its message.
Writing the row logs `Benji SMS job dead-lettered` at ERROR, which is the alarm. Rows
cascade with their conversation, in the ORM and in the database (migration 0174), so a
deletion request removes them too. If the conversation was already gone, the row keeps
neither the conversation nor the SID.

One failure leaves no row: a job killed by the 60 s hard time limit. Celery skips the
failure hook then and logs `Hard time limit exceeded` at ERROR, which reaches Sentry. The
50 s soft limit normally ends the job first, through the hook, so it is dead-lettered.
