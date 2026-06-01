#!/usr/bin/env python3
"""Rotate the engineering on-call assignment in Slack.

Computes who is on-call for the current week from `rotation.json`, then:
  1. Updates a Slack user group (e.g. @oncall) to contain only that person.
  2. Posts a handoff announcement in the configured channel.
  3. Sets the channel topic to show the current on-call (best effort).

Designed to run weekly via GitHub Actions, but works locally too.

Required environment variables:
  SLACK_BOT_TOKEN     Bot token (xoxb-...) with scopes:
                        usergroups:write, chat:write, channels:manage
                        (groups:write for private channels)
  SLACK_USERGROUP_ID  The user group ID to update (e.g. S01ABC2DEF).
  SLACK_CHANNEL_ID    Channel to announce in + set topic on (e.g. C01ABC2DEF).

Optional:
  ONCALL_CONFIG       Path to rotation.json (default: alongside this script).
  ONCALL_DRY_RUN      If set to "1"/"true", print actions without calling Slack.
  ONCALL_TODAY        Override today's date (YYYY-MM-DD) for testing.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

SLACK_API = "https://slack.com/api"


def _bool_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def load_config() -> dict:
    config_path = Path(os.environ.get("ONCALL_CONFIG", Path(__file__).with_name("rotation.json")))
    try:
        data = json.loads(config_path.read_text())
    except FileNotFoundError:
        sys.exit(f"Config not found: {config_path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"Config is not valid JSON ({config_path}): {exc}")

    members = data.get("members") or []
    if not members:
        sys.exit("Config error: `members` is empty.")
    for i, m in enumerate(members):
        if not m.get("slack_id") or m["slack_id"].startswith("U_REPLACE_ME"):
            sys.exit(
                f"Config error: members[{i}] ({m.get('name', '?')}) has a "
                "placeholder/missing slack_id. Fill in real Slack member IDs."
            )
    try:
        anchor = datetime.strptime(data["anchor_monday"], "%Y-%m-%d").date()
    except (KeyError, ValueError):
        sys.exit("Config error: `anchor_monday` must be a YYYY-MM-DD date.")
    if anchor.weekday() != 0:
        sys.exit(f"Config error: anchor_monday {anchor} is not a Monday.")
    return {"members": members, "anchor": anchor}


def today() -> date:
    override = os.environ.get("ONCALL_TODAY")
    if override:
        return datetime.strptime(override, "%Y-%m-%d").date()
    return date.today()


def _weeks_elapsed(config: dict, ref: date) -> int:
    """Whole weeks between the anchor Monday and the Monday of `ref`'s week."""
    week_monday = ref.fromordinal(ref.toordinal() - ref.weekday())
    return (week_monday - config["anchor"]).days // 7


def current_oncall(config: dict, ref: date) -> dict:
    """Return the member on-call for the week containing `ref`."""
    members = config["members"]
    return members[_weeks_elapsed(config, ref) % len(members)]


def previous_oncall(config: dict, ref: date) -> dict:
    members = config["members"]
    return members[(_weeks_elapsed(config, ref) - 1) % len(members)]


def slack_post(method: str, token: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{SLACK_API}/{method}",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        sys.exit(f"Slack API call {method} failed at the network layer: {exc}")
    if not body.get("ok"):
        sys.exit(f"Slack API call {method} returned error: {body.get('error')}")
    return body


def main() -> int:
    config = load_config()
    ref = today()
    on_call = current_oncall(config, ref)
    previous = previous_oncall(config, ref)

    dry_run = _bool_env("ONCALL_DRY_RUN")
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    usergroup = os.environ.get("SLACK_USERGROUP_ID", "")
    channel = os.environ.get("SLACK_CHANNEL_ID", "")

    mention = f"<@{on_call['slack_id']}>"
    prev_mention = f"<@{previous['slack_id']}>"
    announce = (
        f":pager: *On-call this week:* {mention} ({on_call['name']})\n" f"Thanks for your shift, {prev_mention}! :wave:"
    )
    topic = f"On-call: {on_call['name']}"

    if dry_run:
        print("[DRY RUN] No Slack calls will be made.")
        print(f"  Week of:     {ref}")
        print(f"  On-call now: {on_call['name']} ({on_call['slack_id']})")
        print(f"  Previous:    {previous['name']} ({previous['slack_id']})")
        print(f"  Usergroup:   {usergroup or '(unset)'} -> [{on_call['slack_id']}]")
        print(f"  Channel:     {channel or '(unset)'}")
        print(f"  Announce:    {announce!r}")
        print(f"  Topic:       {topic!r}")
        return 0

    missing = [
        n
        for n, v in (
            ("SLACK_BOT_TOKEN", token),
            ("SLACK_USERGROUP_ID", usergroup),
            ("SLACK_CHANNEL_ID", channel),
        )
        if not v
    ]
    if missing:
        sys.exit(f"Missing required env vars: {', '.join(missing)}")

    # 1. Point the user group at the current on-call person.
    slack_post(
        "usergroups.users.update",
        token,
        {"usergroup": usergroup, "users": on_call["slack_id"]},
    )
    # 2. Announce the handoff.
    slack_post("chat.postMessage", token, {"channel": channel, "text": announce})
    # 3. Update the channel topic (best effort; don't fail the run on topic error).
    try:
        slack_post(
            "conversations.setTopic",
            token,
            {"channel": channel, "topic": topic},
        )
    except SystemExit as exc:
        print(f"Warning: could not set channel topic: {exc}", file=sys.stderr)

    print(f"On-call updated: {on_call['name']} ({on_call['slack_id']}) for week of {ref}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
