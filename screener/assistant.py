"""Benbot assistant proxy views.

These are the Layer 1 (browser-facing) endpoints. They authenticate/resolve the
screen, enforce the `benbot` feature flag, assemble the screen context, and proxy
to mfb-ai-service (Layer 2). The browser never calls mfb-ai-service directly.

The context assembled here is the assistant's entire world: mfb-ai-service is
stateless about our domain, and the assistant may only recommend programs from the
lists it's given. So `eligible_programs` has to equal what the results page shows,
and programs the household already receives have to arrive separately in
`current_programs` — otherwise the assistant recommends things the user can't see,
or tells them to apply for benefits they already have (MFB-1427).

See the ai-service repo's docs/ for the full API contract.
"""

import os
from typing import Optional

import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, views
from rest_framework.response import Response

from programs.models import Program
from translations.models import BLANK_TRANSLATION_PLACEHOLDER

from .models import EligibilitySnapshot, Screen

# Where mfb-ai-service lives, and the shared service token (must match the
# service's SERVICE_AUTH_TOKEN). Both come from the environment.
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8080")
AI_SERVICE_TOKEN = os.getenv("AI_SERVICE_TOKEN", "")
AI_SERVICE_TIMEOUT = 60

# Upper bound on the client-supplied visible-programs list. Comfortably above the
# largest white label's active program count; exists to bound untrusted input.
MAX_VISIBLE_PROGRAMS = 256

# Sanity ceiling on a client-supplied program value, in whole dollars. No real annual
# benefit approaches this; it exists so a garbled value can't be quoted at someone.
MAX_PROGRAM_VALUE = 1_000_000

# Relations _build_context reads per program. Both are per-program lookups, so without
# these the query count grows with the number of eligible programs:
#   current_benefits__program -> screen.has_benefit()
#   household_members__insurance -> screen.has_insurance_types() (and the reverse
#       OneToOne `member.insurance`, which hasattr() would otherwise query per member)
CONTEXT_PREFETCH = ("current_benefits__program", "household_members__insurance")


def _ai_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if AI_SERVICE_TOKEN:
        headers["Authorization"] = f"Bearer {AI_SERVICE_TOKEN}"
    return headers


def _translated(translation) -> str:
    """Resolve a parler Translation to text, or "" if there isn't any.

    Pins the language first, the same way `screener.views.default_message` does.
    Without that, `.text` is read in whatever language the request happens to be
    in — and non-default rows are created with `text=""` (translations.models
    `add_translation`), which means parler's `hide_untranslated` fallback never
    fires because the row exists. The result would be empty strings on any
    non-English request rather than the English name.
    """
    try:
        translation.set_current_language(settings.LANGUAGE_CODE)
        text = (translation.text or "").strip()
    except Exception:
        return ""
    return "" if text == BLANK_TRANSLATION_PLACEHOLDER else text


def _latest_snapshot(screen: Screen):
    """Most recent successful, non-batch eligibility snapshot for this screen.

    The results page computes one of these on load, so by the time the user
    opens the assistant there is normally a fresh snapshot to read — far cheaper
    than recomputing eligibility (which calls PolicyEngine).
    """
    try:
        return (
            EligibilitySnapshot.objects.filter(screen=screen, is_batch=False, had_error=False)
            .prefetch_related("program_snapshots")
            .latest("submission_date")
        )
    except EligibilitySnapshot.DoesNotExist:
        return None


def _apply_urls_by_name(screen: Screen, name_abbreviations: list[str]) -> dict[str, str]:
    """Map name_abbreviated -> apply link for the given programs (one query).

    apply_button_link is a translated field, resolved through `_translated` so the
    language is pinned and blank/placeholder links come back empty — the assistant
    must never receive an empty or placeholder URL, since it's instructed to treat
    the links it's given as the only ones it may share.
    """
    if not name_abbreviations:
        return {}

    programs = (
        Program.objects.filter(
            white_label=screen.white_label,
            name_abbreviated__in=name_abbreviations,
        )
        .select_related("apply_button_link")
        .prefetch_related("apply_button_link__translations")
    )

    urls: dict[str, str] = {}
    for program in programs:
        link = _translated(program.apply_button_link)
        if link:
            urls[program.name_abbreviated] = link
    return urls


def _current_programs(screen: Screen) -> list[dict]:
    """The programs this household told us they already receive.

    Read straight from the CurrentBenefit join table rather than the eligibility
    snapshot, so a benefit the household reported is included even when it has no
    snapshot row (not offered by the white label's calculators, or reported after
    the last snapshot was computed).

    Deliberately carries no estimated_value (the screening estimates what they
    *would* get, which is misleading for a benefit already in payment) and no
    apply_url (the assistant must never send them to apply again).
    """
    # One joined query through the CurrentBenefit table, plus one prefetch for the
    # translation rows. `name` is an FK to Translation, but Translation is a parler
    # TranslatableModel whose text lives in a separate table — so select_related
    # alone still resolves `.text` per row. `currentbenefit` is the default reverse
    # accessor; CurrentBenefit.program declares no related_name.
    #
    # White-label scoped like its sibling _apply_urls_by_name: the write path in
    # serializers._write_current_benefits is scoped too, so this is belt-and-braces,
    # but a foreign program leaking into a list the prompt calls a closed universe
    # is worth one extra WHERE clause. Deactivated programs are intentionally NOT
    # filtered out — a program can be discontinued and still be in payment.
    programs = (
        Program.objects.filter(currentbenefit__screen=screen, white_label=screen.white_label)
        .select_related("name")
        .prefetch_related("name__translations")
    )

    current = []
    for program in programs:
        current.append(
            {
                "external_name": program.name_abbreviated,
                # Fall back to the abbreviation so the assistant can still name the
                # program when the translation is missing or blank.
                "name": _translated(program.name) or program.name_abbreviated,
            }
        )

    current.sort(key=lambda p: p["name"])
    return current


def _has_member_insurance(screen: Screen, name_abbreviated: str) -> bool:
    """True if any household member already holds this program's insurance.

    Enrollment lives in TWO independent systems. `CurrentBenefit` (read via
    `screen.has_benefit`) is household-level and covers most programs; medicaid, CHP,
    medicare, VA, emergency medicaid and family planning are member-level and live in
    `Insurance.insurance_map()` instead — deliberately, per the note in
    `serializers._derived_current_benefit_names`. Without this check a household
    already on Medicaid gets Medicaid recommended.

    Coarser than the results page, which reduces a program's value per covered member
    rather than hiding it outright (see `FormattedValue.programValue`). We can't
    reproduce that here — the snapshot stores no member breakdown — so this errs
    toward silence. `strict=False` makes it safe to call for every program: names
    absent from `insurance_map` return False.
    """
    return screen.has_insurance_types((name_abbreviated,), strict=False)


def _build_context(screen: Screen, visible_programs: Optional[list[dict]] = None) -> dict:
    """Assemble the screen context passed to mfb-ai-service.

    Pulls the eligible programs from the latest snapshot, highest-value first, so
    the assistant can prioritize and explain them. Returns an empty list if no
    snapshot exists yet (the contract allows this).

    `eligible_programs` must mirror what the results page actually shows the user —
    the assistant may only recommend from this list, so anything in it that the user
    can't see becomes a recommendation they can't act on.

    Two mechanisms keep it aligned:

    1. `visible_programs`, when the client sends it, is the authoritative set: the
       `name_abbreviated`s the results page is rendering right now. Several of its
       filters run client-side and can't be reproduced here (legal status /
       citizenship, `excludes_programs` mutual exclusions, and per-member insurance,
       which the snapshot has no member breakdown for), so we intersect rather than
       re-derive.
    2. The server-side filters below are the fallback for clients that don't send it
       (older frontend builds, and non-web channels per ADR-002). They cover the gates
       we *can* reproduce: already-received programs, $0 rows, and household-level
       insurance enrollment.

    Already-received programs move to `current_programs` rather than disappearing, so
    the assistant keeps the context to answer questions about them.
    """
    eligible_programs = []
    snapshot = _latest_snapshot(screen)
    if snapshot is not None:
        visible = {p["name_abbreviated"]: p for p in visible_programs} if visible_programs is not None else None
        rows = [
            p
            for p in snapshot.program_snapshots.all()
            if p.eligible
            and (p.estimated_value or 0) > 0
            and not screen.has_benefit(p.name_abbreviated)
            and not _has_member_insurance(screen, p.name_abbreviated)
            and (visible is None or p.name_abbreviated in visible)
        ]

        def displayed_value(row) -> Optional[int]:
            """The figure the user is looking at, preferring the client's.

            The results page reduces a program's value by each member who already
            holds its insurance (`FormattedValue.programValue`), while the snapshot's
            `estimated_value` sums *all* members. For a household where some but not
            all members are covered the two differ — and the assistant quoting a
            number the user can't find anywhere is its own kind of failure. The
            frontend already computed the displayed figure, so we take it when offered
            and fall back to the snapshot otherwise.
            """
            entry = visible.get(row.name_abbreviated) if visible else None
            if entry is not None and entry.get("value") is not None:
                return entry["value"]
            return int(row.estimated_value) if row.estimated_value is not None else None

        # Sort by what the user sees, so "your biggest one" agrees with their screen.
        rows.sort(key=lambda p: displayed_value(p) or 0, reverse=True)
        apply_urls = _apply_urls_by_name(screen, [p.name_abbreviated for p in rows])
        for p in rows:
            # The snapshot's `name` was captured as `program.name.text` under whatever
            # language was active when eligibility ran (screener.views, unpinned), and
            # non-default translation rows are created with text="". So a snapshot
            # computed under a non-English request can hold "" or the placeholder —
            # which would render as "- (wa_snap)" in the prompt. Same fallback as
            # _current_programs.
            snapshot_name = (p.name or "").strip()
            if snapshot_name == BLANK_TRANSLATION_PLACEHOLDER:
                snapshot_name = ""
            program = {
                "external_name": p.name_abbreviated,
                "name": snapshot_name or p.name_abbreviated,
                # Whole dollars. Frequency is governed by value_type; see the
                # API contract's open question on units.
                "estimated_value": displayed_value(p),
                "estimated_application_time": p.estimated_application_time,
            }
            apply_url = apply_urls.get(p.name_abbreviated)
            if apply_url:
                program["apply_url"] = apply_url
            eligible_programs.append(program)

    return {
        "household": {"size": screen.household_size},
        "eligible_programs": eligible_programs,
        "current_programs": _current_programs(screen),
        # The assistant's guardrails offer "your results page" as the fallback when
        # it has nothing it may recommend. That fallback was dead — this key was
        # never sent, so on an empty eligible list the model had no legitimate exit
        # at all. Same URL shape the results email uses
        # (integrations.services.communications.message).
        "results_url": f"{settings.FRONTEND_DOMAIN}/{screen.white_label.code}/{screen.uuid}/results/benefits",
    }


def _visible_programs(request) -> Optional[list[dict]]:
    """Parse and sanitize the client's `visible_programs` list.

    Accepts either shape, so an older frontend build keeps working:
      ["snap", "wic"]                              (names only)
      [{"name_abbreviated": "snap", "value": 6636}] (names + displayed values)

    Returns a normalized list of `{"name_abbreviated": str, "value": int | None}`.

    Untrusted browser input, so it's bounded and type-checked. Names can only ever
    *narrow* the program list (they're intersected with the snapshot in
    `_build_context`), so a hostile value can't smuggle a program in. `value` is the
    one field that is *trusted* — it's what the user is looking at, which is the whole
    point — so it's range-checked, and anything suspect falls back to the snapshot's
    figure rather than being sent to the model.

    Returns None when the key is absent or unusable, which selects the server-side
    fallback filters instead. An explicitly empty list is meaningful and preserved:
    it means the results page is rendering nothing.
    """
    # request.data is a list for a JSON array body, so don't assume .get exists.
    raw = request.data.get("visible_programs") if isinstance(request.data, dict) else None
    if not isinstance(raw, list):
        return None

    programs: list[dict] = []
    for item in raw[:MAX_VISIBLE_PROGRAMS]:
        if isinstance(item, str):
            name, value = item, None
        elif isinstance(item, dict):
            name = item.get("name_abbreviated")
            value = item.get("value")
        else:
            continue
        if not isinstance(name, str) or not name.strip():
            continue
        programs.append({"name_abbreviated": name.strip().lower(), "value": _clean_value(value)})

    # A list that had content but survived as nothing is malformed input, not a
    # genuine "results page is empty" — fall back rather than blank the assistant.
    if raw and not programs:
        return None
    return programs


def _clean_value(value) -> Optional[int]:
    """Coerce a client-supplied displayed value to whole dollars, or None.

    None means "no usable value, use the snapshot's". Bools are rejected explicitly
    (`isinstance(True, int)` is True in Python). Negative and absurd values are
    dropped rather than quoted at someone as a benefit amount.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")):  # NaN / inf
        return None
    if value < 0 or value > MAX_PROGRAM_VALUE:
        return None
    return int(value)


def _proxy(method: str, path: str, json_body: dict) -> Response:
    """Forward a request to mfb-ai-service and pass its response through."""
    try:
        resp = requests.request(
            method,
            f"{AI_SERVICE_URL}{path}",
            json=json_body,
            headers=_ai_headers(),
            timeout=AI_SERVICE_TIMEOUT,
        )
    except requests.RequestException as e:
        return Response(
            {"error": {"code": "ai_upstream_error", "message": str(e)}},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    try:
        body = resp.json()
    except ValueError:
        body = {"error": {"code": "ai_upstream_error", "message": "Non-JSON response from AI service."}}
        return Response(body, status=status.HTTP_502_BAD_GATEWAY)
    return Response(body, status=resp.status_code)


class AssistantStartView(views.APIView):
    """POST: open (or resume) a Benbot conversation for a screen."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, screen_uuid):
        # CONTEXT_PREFETCH keeps _build_context's per-program enrollment checks on the
        # zero-query path. _current_programs still issues its own query — it needs the
        # translated names, which these prefetches don't carry.
        screen = get_object_or_404(
            Screen.objects.prefetch_related(*CONTEXT_PREFETCH),
            uuid=screen_uuid,
        )
        if not screen.white_label.has_feature("benbot"):
            return Response({"error": {"code": "assistant_disabled"}}, status=status.HTTP_403_FORBIDDEN)

        payload = {
            "screen_uuid": str(screen.uuid),
            "white_label": screen.white_label.code,
            "locale": request.data.get("locale", "en-US"),
            "context": _build_context(screen, _visible_programs(request)),
        }
        return _proxy("POST", "/v1/conversations", payload)


class AssistantMessageView(views.APIView):
    """POST: send a user message to an existing Benbot conversation."""

    permission_classes = [permissions.AllowAny]

    def post(self, request, screen_uuid, conversation_id):
        screen = get_object_or_404(Screen, uuid=screen_uuid)
        if not screen.white_label.has_feature("benbot"):
            return Response({"error": {"code": "assistant_disabled"}}, status=status.HTTP_403_FORBIDDEN)

        payload = {
            "text": request.data.get("text", ""),
            "client_message_id": request.data.get("client_message_id"),
        }
        return _proxy("POST", f"/v1/conversations/{conversation_id}/messages", payload)
