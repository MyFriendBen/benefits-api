# Benji SMS inbound webhook

Where Twilio posts each text sent to our number (MFB-2439; design: MFB-1916 proposal v3,
decisions 3, 4, 5, 7 and 10). The webhook checks Twilio's signature, works out what state
the sending number is in, and either answers with a fixed reply or queues a turn for the
worker ([BENJI_SMS_WORKER.md](BENJI_SMS_WORKER.md)). It never calls the model.

## What runs where

| Piece | Where |
| --- | --- |
| The view (signature, form fields, status code) | `screener/benji_sms_inbound.py` |
| The decision table | `integrations/services/communications/benji_sms_inbound.py` |
| Signature check | `integrations/services/communications/twilio_signature.py` |
| STOP / HELP / START word lists | `integrations/services/communications/benji_sms_keywords.py` |
| Fixed reply text | `integrations/services/communications/benji_sms_replies.py` |
| Sends, and the gates in front of them | `integrations/services/communications/benji_sms.py` |
| Media deletion job | `screener.benji_sms_delete_media` in `screener/tasks.py` |
| Local testing | `manage.py fake_benji_sms_inbound` |

## URLs to set on the Twilio number

Both are set on the number (or its Messaging Service) in the Twilio console, per
environment. Nothing points at production until launch (MFB-2447).

| Twilio setting | URL |
| --- | --- |
| A message comes in (HTTP POST) | `<BACKEND_DOMAIN>/api/assistant/sms/inbound/#rc=2&rp=ct,rt,5xx&ct=3000&rt=5000` |
| Primary handler fails (HTTP POST) | `<BACKEND_DOMAIN>/api/assistant/sms/inbound/fallback/#rc=2&rp=ct,rt,5xx&ct=3000&rt=5000` |

- `#rc=2&rp=ct,rt,5xx&ct=3000&rt=5000` is Twilio's connection override: retry twice when
  Twilio cannot connect, times out, or gets a 5xx. All attempts share Twilio's 15-second
  total (`tt`), so the read timeout is cut to 5 s (`rt`) and the connect timeout to 3 s
  (`ct`): with the defaults, one slow attempt would use the whole 15 s and leave no time
  for a retry. A normal answer takes well under a second; the slowest path (a fixed
  reply sent through Twilio inside the request) is bounded by the 10 s Twilio client
  timeout, and a replay of it is safe. Without it Twilio retries only a failed connection,
  and goes straight to the fallback URL on a 5xx. A 4xx is left out on purpose: a 403
  (bad signature) or 400 will not change on a retry. The fragment is not sent to us and
  is not part of the signature. Twilio does not say whether it honours a fragment on the
  fallback URL; it is harmless if it does not.
- **Known gap: a queue outage longer than Twilio's retry window loses the text.** Twilio
  caps all attempts at 15 seconds in total (`tt`, at most 15000 ms), so retries cannot
  cover an outage of the broker. The webhook answers 503 when it cannot queue a turn or a
  media deletion; once Twilio has given up, that text is not answered and, if it carried
  a picture, its media stays at Twilio. Each case leaves a `Benji SMS inbound webhook
  failed` ERROR log; when the text itself was handled and only its media deletion could
  not be queued, the outcome line is logged too. Anything the text changed (a STOP, a
  START) is applied before the queueing, so consent is never lost this way. A sweep of recent inbound media at Twilio
  would close the media half; it belongs with the nightly sweep (MFB-2442).
- **`BACKEND_DOMAIN` must be the public https origin written in those URLs**, exactly.
  The signature is checked against `BACKEND_DOMAIN` plus the request path, not against
  the `Host` header. If the two differ, every text is refused with a 403.
- `TWILIO_TOKEN` must be the auth token of the account that owns the number. With no
  token, every request is refused.
- The Celery broker (`CELERY_BROKER_URL`, [BENJI_SMS_WORKER.md](BENJI_SMS_WORKER.md))
  must be attached before a number points here. Without it every text that needs a
  queue (any picture, any turn) is answered 503, and Twilio counts each as a webhook
  error.
- Keep the trailing slash. Twilio signs the URL as written.

## What happens to a text

In order, first match wins.

| # | The text is | What we do | Reply |
| --- | --- | --- | --- |
| 0 | Not signed by Twilio | 403, before any database read | none |
| 1 | From something that is not a phone number | Nothing | none |
| 2 | From an unknown number, and our HELP word (`ayuda`) | | Stranger reply, once a day |
| 3 | From an unknown number, and any other keyword | Nothing | none |
| 4 | From an unknown number | | Stranger reply (English and Spanish), once a day |
| 5 | STOP | Revoke the number, close its conversation | Ours, if the wording is ours |
| 6 | START, from a revoked number | Clear the revocation; resume the conversation the STOP closed, if it can | Ours, if the wording is ours |
| 7 | START, from a number that is not revoked | Nothing ("yes" is an ordinary answer and carries on) | none |
| 8 | Anything else from a revoked number | Nothing | none |
| 9 | HELP | Nothing | Ours, if the wording is ours |
| 10 | From a phone marked shared | | Shared-phone reply, once a day |
| 11 | The first after 90 quiet days | Expire the conversation, then as 12 | |
| 12 | From a number with no active conversation | | Re-entry reply, once a day |
| 13 | For a white label with the flag or kill switch off | Nothing | none |
| 14 | Carrying media | Record the inbound time | "Can't read pictures yet" |
| 15 | Anything else | Record the inbound time, queue the turn | none (the worker replies) |

Then, for every text carrying media, whatever happened above: queue the deletion of the
media at Twilio. It comes last so that a broker outage cannot hold up a STOP.

Every text is answered with `200` and empty TwiML, except a `403` for row 0, a `400` for
a signed request with no `MessageSid`, and a `503` when a turn or a media deletion could
not be queued, which makes Twilio post the text again (see the known gap above).

STOP and START (rows 5 to 7) are decided with the phone's row locked, on a fresh read of
the revocation, so a STOP and a START sent together are applied in order. The quiet check
and the inbound-time write (rows 11, 14 and 15) run with the binding's row locked, so two
texts arriving together cannot expire a conversation the other one has just kept alive.
Every other branch that sends or queues something re-reads the revocation first, so a
STOP that lands while a text is being handled stops its reply. The send itself is not
under a lock, so a STOP landing in the last moment before it can still be beaten; the
worker (MFB-2440) has to check again before it replies.

### Who answers STOP, HELP and START

Twilio handles its own keywords before our webhook runs: it replies itself, and after a
STOP it blocks anything we send to that number (error 21610). So for Twilio's words
(`stop`, `stopall`, `unsubscribe`, `cancel`, `end`, `quit`, `revoke`, `optout`; `help`,
`info`; `start`, `yes`, `unstop`) we only change state.

Our own fixed replies go out for the wordings Twilio does not handle: Spanish (`alto`,
`ayuda`, `iniciar`, ...) and longer English (`please stop`, `stop texting me`, ...). A
Twilio word with punctuation around it (`Stop.`) counts as ours too; if Twilio did act on
it, our confirmation fails with 21610 and is dropped, which is logged as a warning.

If the number's Messaging Service has Advanced Opt-Out on, Twilio sends `OptOutType`,
and that settles it: Twilio handled the message.

Only a whole message matches. "stop sending me to that website" goes to the model, and
so does a keyword followed by words in any other script ("stop 我的福利").

START always clears the revocation. The conversation resumes only if it is the one the
STOP closed, is inside the 90-day interval, and no other phone has since taken the screen.
Otherwise the next text gets the re-entry reply. A START that resumes the conversation
counts as an inbound text, so the 90 days restart from it.

A stranger (a number that never used the on-ramp) who texts our HELP word gets the
stranger reply, which says who we are and how to stop; Twilio does not answer that
wording. Our STOP and START words from a stranger get nothing: we never text a stranger
unprompted, and there is nothing to restart.

### Once a day

The stranger, shared-phone and re-entry replies share one limit: a number gets one of
them a day, however often it texts. The memory is a `BenjiSmsStrangerReply` row, meant to
be purged after a day by the nightly sweep (MFB-2442). In Postgres, not the cache, so the limit holds when Redis is down.

If the reply definitely did not go out for a reason that may pass (a gate refused it, or
Twilio was unreachable, rate limiting or failing), the day's claim is given back, so the
number's next text tries again. A refusal about the number itself (an invalid number, an
opted-out one) keeps the claim: it would be refused again. An unknown outcome (Twilio
may have accepted it) keeps it too.

### A replayed webhook changes nothing new

Twilio posts a text again when our answer does not reach it in time, and through the
fallback URL after that.

- Each fixed reply first inserts its `BenjiSmsDelivery` row, and the database allows one
  fixed reply per inbound `MessageSid` (`benji_sms_delivery_one_fixed_per_inbound`), so a
  replay loses the insert and sends nothing. It is claimed before the day's limit, so a
  replay never spends the number's allowance.
- Every decision for a text from a known number is recorded with its `MessageSid` in a
  `BenjiSmsInboundReceipt`: STOP and START in the same locked transaction as their
  change (even when they changed nothing), every other decision before its work is
  done. A replay follows that first decision and redoes only its unfinished work: it
  queues the turn again for the conversation it was first queued for (even after a new
  on-ramp), or retries the same fixed reply, whose claim lets one out per text. So an
  older STOP or START cannot undo a newer one, and a text answered as shared does not
  become a turn when the mark lapses. One gap: if the first post failed before its
  decision was recorded (a crash mid-request), the replay decides afresh.
- Confirmations are best effort. A STOP or START made in our wording is confirmed
  ("You won't get more texts", "Benji is back") by the text that made the change, on
  its first post only; Twilio confirms its own keywords. A replay or a repeated keyword
  never sends a confirmation, so nobody gets a stale or second one. If that one send
  fails at Twilio, or the request fails before it, the confirmation is lost; the change
  itself is already applied.
- A replayed turn is queued again and the worker absorbs it (MFB-2440).

## Fixed reply text

Each reply has a translation label (`benji.sms.stranger`, `.shared`, `.reentry`, `.stop`,
`.help`, `.start_resumed`, `.start_reentry`, `.picture`). The text is that label's
translation in the conversation's language, else English, else a default in the code,
with a warning logged when the default is used. `{link}` becomes `FRONTEND_DOMAIN`.
Line breaks in a translation are sent as written.

**The in-code defaults are provisional**, there so staging works before the rows exist.
MFB-2444 adds the rows in all 18 languages. Before launch, no reply should be logging
"no translation".

## Privacy

- Nothing logs the phone number, its hash or the message. Log lines carry the outcome
  (`outcome=queued`), Twilio error codes and exception class names.
- Sentry events from `/api/assistant/sms/` lose the request body, the query string and
  stack locals (`benefits/sentry_scrub.py`). A refused request still produces an event,
  which is what the signature-failure alarm (MFB-2441) will count.
- Media is deleted at Twilio for every text that carries any, whoever sent it.
- Delivery rows for replies to a number with no binding are purged after a day once the
  nightly sweep (MFB-2442) runs it; until that sweep exists, they are kept.
- Inbound receipts (`BenjiSmsInboundReceipt`) keep the `MessageSid` of every text from a
  known number, with what was decided for it, so a replay follows its first decision.
  They are meant to live a day: the nightly sweep (MFB-2442) purges them with
  `BenjiSmsInboundReceipt.objects.purge_expired`, and until that sweep exists they are
  kept. Like the delivery rows' SIDs, they resolve to the number at Twilio; they go with
  the phone row in a deletion request. The phone row also keeps the id of the
  conversation its STOP closed, which is not personal data. Texts from strangers leave
  no receipt.
- Fixed replies ask Twilio for delivery status once the status callback route exists
  (MFB-2441, `benji_sms.status_callback_url`). Until then they are sent without one, so
  Twilio is never told to post to a URL that does not exist.

## Trying it locally

`fake_benji_sms_inbound` signs a request the way Twilio does and posts it to the local
server. Set these in both the server's environment and the command's:

- `BACKEND_DOMAIN`: the server's address (the default, `http://localhost:8000`, matches
  `runserver`).
- `TWILIO_TOKEN`: any string, the same in both.
- `BENJI_SMS_HASH_KEY`: at least 32 characters, the same in both
  (`python -c "import secrets; print(secrets.token_hex(32))"`). Without it every known
  number fails to hash and the webhook answers 503. It identifies every stored phone, so
  never change it on a database that has bindings you want to keep.

```bash
python manage.py fake_benji_sms_inbound "what is snap"
```

```bash
python manage.py fake_benji_sms_inbound alto --from +13035550100
```

```bash
python manage.py fake_benji_sms_inbound "" --media 1
```

```bash
python manage.py fake_benji_sms_inbound hi --url http://localhost:8000/api/assistant/sms/inbound/fallback/
```

With `DEBUG` on, no text reaches Twilio: each send is refused and logged
(`Benji SMS send refused: reason=debug`), and rows that depend on a send are not kept.
Each text logs one `Benji SMS inbound: outcome=...` line at INFO.
To see a turn queued, set `BENJI_SMS_OUTBOUND_ENABLED=true`, turn `benji_sms` on for the
white label, and text from a number that has a binding. Until MFB-2440 lands, the queued
turn is dead-lettered on purpose.
