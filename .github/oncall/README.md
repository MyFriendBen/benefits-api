# Engineering On-Call Rotation

A free, low-maintenance way to make it **obvious who's on call** in Slack and
**auto-cycle** the rotation every week — no PagerDuty, no per-seat cost.

Each Monday morning a GitHub Action runs and:

1. Points a Slack **user group** (`@oncall`) at the current on-call person, so
   anyone can `@oncall` to ping whoever's on duty without knowing who it is.
2. Posts a **handoff announcement** in the engineering channel.
3. Sets the **channel topic** to `On-call: <name>`.

The whole rotation is driven by [`rotation.json`](./rotation.json) — change the
team or order by editing that one file.

---

## One-time setup (~15 min)

### 1. Create a Slack user group

In Slack: **People & user groups → Create user group**. Name it `@oncall`
(handle `oncall`). It can start empty — the script fills it.

Grab its ID: open the group, and the URL ends in something like
`...?subteam=S01ABC2DEF`. That `S...` value is your `SLACK_USERGROUP_ID`.

### 2. Create a Slack app + bot token

1. Go to <https://api.slack.com/apps> → **Create New App → From scratch**.
2. Under **OAuth & Permissions**, add these **Bot Token Scopes**:
   - `usergroups:write` — update the on-call group
   - `chat:write` — post the handoff message
   - `channels:manage` — set the topic of a public channel
     (use `groups:write` instead if the channel is private)
   - `channels:history` — read recent messages so the daily catch-up run can
     tell whether this week's handoff was already announced
     (use `groups:history` instead if the channel is private). If this scope
     is missing the script still works — it just falls back to posting, which
     may duplicate the announcement on catch-up days.
3. **Install to Workspace** and copy the **Bot User OAuth Token** (`xoxb-...`).
   This is your `SLACK_BOT_TOKEN`.
4. Invite the bot to your channel: in the channel, `/invite @YourAppName`.

### 3. Get the channel ID

In Slack, open the channel → click its name → the **About** tab shows a
**Channel ID** (`C01ABC2DEF`) at the bottom. That's `SLACK_CHANNEL_ID`.

### 4. Add the GitHub repository secrets

In **benefits-api**: **Settings → Secrets and variables → Actions → New
repository secret**. Add:

| Secret               | Value        |
| -------------------- | ------------ |
| `SLACK_BOT_TOKEN`    | `xoxb-...`   |
| `SLACK_USERGROUP_ID` | `S01ABC2DEF` |
| `SLACK_CHANNEL_ID`   | `C01ABC2DEF` |

### 5. Confirm the rotation

The team is already filled in in [`rotation.json`](./rotation.json):

- `members` is the rotation, in order. Get a Slack member ID from a person's
  profile → **⋮ → Copy member ID** (`U01ABC2DEF`).
- `anchor_monday` is a **Monday** used as week 0. The person at `members[0]` is
  on-call that week; the rotation advances by one each week.

That's it. The workflow runs automatically every Monday at ~9am Denver time.

---

## Test it before going live

Dry-run locally (no Slack calls, no tokens needed):

```bash
ONCALL_DRY_RUN=1 python .github/oncall/rotate_oncall.py

# See who's on-call for a specific week:
ONCALL_DRY_RUN=1 ONCALL_TODAY=2026-07-15 python .github/oncall/rotate_oncall.py
```

Or trigger the real workflow on demand: **Actions → Weekly On-Call Rotation →
Run workflow**, with the **Dry run** box checked to preview, or unchecked to
actually post.

---

## How the schedule math works

The script computes whole weeks elapsed since `anchor_monday` and indexes into
`members` with modulo, so it's **stateless and idempotent** — running it twice
in a week (e.g. the two DST-spanning cron entries) just re-applies the same
assignment. No database, no drift.

### Catch-up safety net

GitHub Actions' `schedule` trigger is **best-effort**: under load it delays
runs and sometimes drops them entirely, so the Monday fire can silently never
happen. To cover that, the workflow also runs mid-morning Tue–Fri. On those
catch-up runs the script re-applies the (idempotent) usergroup + topic, and
posts the handoff announcement **only if it wasn't already posted this week**
(checked via `conversations.history`). So a missed Monday self-heals by the
next morning without re-spamming the channel on weeks Monday worked fine.

If GitHub ever drops a run, you can also force one immediately: **Actions →
Weekly On-Call Rotation → Run workflow**, or `gh workflow run
oncall-rotation.yml --ref main`.

## Changing the rotation

- **Add/remove/reorder people:** edit `members` in `rotation.json`. Order is the
  rotation order.
- **Skip a week / cover for someone:** easiest is a temporary manual edit to the
  user group membership in Slack; the next Monday run resets it to the schedule.
- **Reset the cycle:** change `anchor_monday` to a Monday and put whoever should
  go first at `members[0]`.

## Cost

Free. GitHub Actions scheduled workflows are included on free plans, and this
runs ~5 seconds a week. Slack user groups + the API are free on any paid Slack
plan.
