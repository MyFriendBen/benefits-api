# Benji SMS inbound webhook

Where Twilio posts each text sent to our number (MFB-2439; design: MFB-1916 proposal v3,
decisions 3, 4, 5, 7 and 10). The webhook checks Twilio's signature, works out what state
the sending number is in, and either answers with a fixed reply or queues a turn for the
worker ([BENJI_SMS_WORKER.md](BENJI_SMS_WORKER.md)). It never calls the model.

## What runs where

| Piece | Where |
| --- | --- |
| The view and the decision table | `screener/benji_sms_inbound.py` |
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
| A message comes in (HTTP POST) | `<BACKEND_DOMAIN>/api/assistant/sms/inbound/#rc=2&rp=all` |
| Primary handler fails (HTTP POST) | `<BACKEND_DOMAIN>/api/assistant/sms/inbound/fallback/` |

- `#rc=2&rp=all` is Twilio's connection override: retry twice, on any failure. Twilio's
  default is one retry and only when it cannot connect. The fragment is not sent to us
  and is not part of the signature.
- **`BACKEND_DOMAIN` must be the public https origin written in those URLs**, exactly.
  The signature is checked against `BACKEND_DOMAIN` plus the request path, not against
  the `Host` header. If the two differ, every text is refused with a 403.
- `TWILIO_TOKEN` must be the auth token of the account that owns the number. With no
  token, every request is refused.
- Keep the trailing slash. Twilio signs the URL as written.

## What happens to a text

In order, first match wins.

| # | The text is | What we do | Reply |
| --- | --- | --- | --- |
| 0 | Not signed by Twilio | 403, before any database read | none |
| 1 | Carrying media, in any state | Queue deletion of the media at Twilio, then carry on | |
| 2 | From something that is not a phone number | Nothing | none |
| 3 | From an unknown number, and a keyword | Nothing | none |
| 4 | From an unknown number | | Stranger reply (English and Spanish), once a day |
| 5 | STOP | Revoke the number, close its conversation | Ours, if the wording is ours |
| 6 | START, from a revoked number | Clear the revocation; resume the conversation if it can | Ours, if the wording is ours |
| 7 | Anything else from a revoked number | Nothing | none |
| 8 | HELP | Nothing | Ours, if the wording is ours |
| 9 | START, from a number that is not revoked | Nothing ("yes" is an ordinary answer and carries on) | none |
| 10 | From a phone marked shared | | Shared-phone reply, once a day |
| 11 | The first after 90 quiet days | Expire the conversation, then as 12 | |
| 12 | From a number with no active conversation | | Re-entry reply, once a day |
| 13 | For a white label with the flag or kill switch off | Nothing | none |
| 14 | Carrying media | Record the inbound time | "Can't read pictures yet" |
| 15 | Anything else | Record the inbound time, queue the turn | none (the worker replies) |

Every text is answered with `200` and empty TwiML, except a `403` for row 0, a `400` for
a signed request with no `MessageSid`, and a `503` when a turn or a media deletion could
not be queued, which makes Twilio post the text again.

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

Only a whole message matches. "stop sending me to that website" goes to the model.

START always clears the revocation. The conversation resumes only if its binding was
closed (not expired), is inside the 90-day interval, and no other phone has since taken
the screen. Otherwise the next text gets the re-entry reply.

### Once a day

The stranger, shared-phone and re-entry replies share one limit: a number gets one of
them a day, however often it texts. The memory is a `BenjiSmsStrangerReply` row, purged
after a day. In Postgres, not the cache, so the limit holds when Redis is down.

### A replayed webhook sends nothing new

Twilio posts a text again when our answer does not reach it in time, and through the
fallback URL after that. Each fixed reply first inserts its `BenjiSmsDelivery` row, and
the database allows one fixed reply per inbound `MessageSid`
(`benji_sms_delivery_one_fixed_per_inbound`), so a replay loses the insert and sends
nothing. The state changes are all safe to repeat. A replayed turn is queued again and
the worker absorbs it (MFB-2440).

Known gap: a revoked number's "yes" clears the revocation, so a replay of that one text
finds the number no longer revoked and queues "yes" as a turn.

## Fixed reply text

Each reply has a translation label (`benji.sms.stranger`, `.shared`, `.reentry`, `.stop`,
`.help`, `.start_resumed`, `.start_reentry`, `.picture`). The text is that label's
translation in the conversation's language, else English, else a default in the code,
with a warning logged when the default is used. `{link}` becomes `FRONTEND_DOMAIN`.

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
- Delivery rows for replies to a number with no binding are purged after a day.

## Trying it locally

`fake_benji_sms_inbound` signs a request the way Twilio does and posts it to the local
server. `BACKEND_DOMAIN` must match the server's address (the default,
`http://localhost:8000`, does), and `TWILIO_TOKEN` can be any string.

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
To see a turn queued, set `BENJI_SMS_OUTBOUND_ENABLED=true`, turn `benji_sms` on for the
white label, and text from a number that has a binding. Until MFB-2440 lands, the queued
turn is dead-lettered on purpose.
