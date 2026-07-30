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

import logging
import os
from typing import Optional

import requests
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import get_language
from rest_framework import permissions, status, views
from rest_framework.response import Response
from sentry_sdk import capture_message

from programs.models import Program
from translations.models import BLANK_TRANSLATION_PLACEHOLDER

from .models import EligibilitySnapshot, Insurance, Screen
from .views import HashedIPAnonRateThrottle

logger = logging.getLogger(__name__)

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

# Cap on any DB-sourced string that reaches ai-service's system prompt. Program names
# are editable by admins/translators, so this bounds how much can be smuggled into the
# highest-trust position in the request.
MAX_PROMPT_FIELD_LEN = 160

# Keys in Insurance.insurance_map() that describe a coverage *source* rather than a
# MyFriendBen program, so they never correspond to a Program row.
_NON_PROGRAM_INSURANCE_KEYS = frozenset({"dont_know", "none", "employer", "private"})

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


def _translated(translation, language_code: Optional[str] = None) -> str:
    """Resolve a parler Translation to text, or "" if there isn't any usable text.

    Tries `language_code` (default: the request's active language), then falls back to
    `settings.LANGUAGE_CODE`. The fallback is necessary because non-default rows are
    created with `text=""` (`translations.models.add_translation`), and because the row
    *exists* parler's `hide_untranslated` never fires — so reading `.text` under a
    Spanish request would yield empty strings rather than the English name.

    Trying the active language *first* matters for `apply_button_link`, where the
    non-English row is often legitimately different (state portals have /es landing
    pages). Pinning straight to LANGUAGE_CODE, as an earlier revision did, silently
    served everyone the English URL.

    Also flattens whitespace and bounds length: these strings are interpolated into
    ai-service's *system* prompt, and `Translation` rows are editable by admins and
    translators, so a name containing newlines plus instruction-shaped text could
    otherwise forge a prompt block. ai-service sanitizes again at render; this is the
    cheap choke point on the way out.
    """
    for lang in (language_code or get_language(), settings.LANGUAGE_CODE):
        if not lang:
            continue
        try:
            translation.set_current_language(lang)
            text = (translation.text or "").strip()
        except AttributeError:
            # A None FK, or parler's TranslationDoesNotExist (an AttributeError
            # subclass). Deliberately narrow — a bare `except Exception` here would
            # swallow OperationalError and silently degrade every name.
            return ""
        if text and text != BLANK_TRANSLATION_PLACEHOLDER:
            return " ".join(text.split())[:MAX_PROMPT_FIELD_LEN]
    return ""


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


def _insurance_program_names(screen: Screen) -> set[str]:
    """`name_abbreviated`s the household holds via the member-level Insurance system.

    Derived from `Insurance.insurance_map()`'s own keys so it can't go stale when a new
    white-label variant is added there. Insurance-type keys that aren't programs
    ("none", "employer", "private", "dont_know") are skipped.
    """
    members = list(screen.household_members.all())
    if not members:
        return set()
    candidates = set(Insurance.insurance_map(Insurance()).keys()) - _NON_PROGRAM_INSURANCE_KEYS
    return {name for name in candidates if screen.has_insurance_types((name,), strict=False)}


def _current_programs(screen: Screen) -> list[dict]:
    """The programs this household told us they already receive.

    Read straight from the CurrentBenefit join table rather than the eligibility
    snapshot, so a benefit the household reported is included even when it has no
    snapshot row (not offered by the white label's calculators, or reported after
    the last snapshot was computed).

    Covers BOTH enrollment systems. `CurrentBenefit` is household-level; medicaid,
    CHP, medicare, VA, emergency medicaid and family planning are member-level in
    `Insurance.insurance_map()` and never written to `CurrentBenefit` (deliberately —
    see `serializers._derived_current_benefit_names`). Without the union, a household
    on Medicaid would have Medicaid removed from `eligible_programs` by
    `_has_member_insurance` AND absent here, so ai-service's closed-world rule would
    forbid the assistant from naming it at all — "why did my Medicaid renewal letter
    arrive?" would get a refusal.

    Deliberately carries no estimated_value (the screening estimates what they
    *would* get, which is misleading for a benefit already in payment) and no
    apply_url (the assistant must never send them to apply again).
    """
    # One joined query through the CurrentBenefit table (unioned with the
    # insurance-derived names), plus one prefetch for the translation rows. `name` is
    # an FK to Translation, but Translation is a parler TranslatableModel whose text
    # lives in a separate table — so select_related alone still resolves `.text` per
    # row. `currentbenefit` is the default reverse accessor; CurrentBenefit.program
    # declares no related_name.
    #
    # White-label scoped like its sibling _apply_urls_by_name: the write path in
    # serializers._write_current_benefits is scoped too, so this is belt-and-braces,
    # but a foreign program leaking into a list the prompt calls a closed universe
    # is worth one extra WHERE clause. Deactivated programs are intentionally NOT
    # filtered out — a program can be discontinued and still be in payment.
    insurance_names = _insurance_program_names(screen)
    criteria = Q(currentbenefit__screen=screen)
    if insurance_names:
        criteria |= Q(name_abbreviated__in=insurance_names)
    programs = (
        Program.objects.filter(criteria, white_label=screen.white_label)
        # distinct() is required now that the Q() union can match a program by both
        # arms; the CurrentBenefit join alone couldn't duplicate (unique_together).
        .distinct()
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

    # casefold, because names that fell back to `name_abbreviated` are lowercase and
    # would otherwise all sort after every translated name.
    current.sort(key=lambda p: p["name"].casefold())
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


def _displayed_value(row, visible: Optional[dict]) -> Optional[int]:
    """The figure the user is looking at, in whole dollars.

    The results page reduces a program's value by each member who already holds its
    insurance (`FormattedValue.programValue`), while the snapshot's `estimated_value`
    sums *all* members. For a household where some but not all members are covered
    the two differ, and the assistant quoting a number the user can't find anywhere is
    its own kind of failure — so we prefer the client's figure.

    Bounded by the snapshot, and that bound is load-bearing rather than cosmetic.
    `AssistantStartView` is `AllowAny` and the screen UUID is also the results-page
    URL, so a third party who has seen a link can POST a start call; ai-service then
    resumes by screen_uuid and overwrites the stored context. Without a bound they
    could make a victim's assistant quote an arbitrary amount. The results page can
    only ever *reduce* the snapshot value, so anything above it is definitionally not
    a displayed value.
    """
    snapshot = int(row.estimated_value) if row.estimated_value is not None else None
    entry = visible.get(row.name_abbreviated) if visible is not None else None
    client = entry.get("value") if entry is not None else None
    if client is None or snapshot is None:
        return snapshot
    return min(client, snapshot)


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
        all_rows = list(snapshot.program_snapshots.all())
        values = {p.name_abbreviated: _displayed_value(p, visible) for p in all_rows}

        rows = [
            p
            for p in all_rows
            if p.eligible
            # Gate on the DISPLAYED figure, not the snapshot's — a client value of 0
            # would otherwise slip a "~$0 per year" program into the list, which is
            # exactly the row the results page hides.
            and (values.get(p.name_abbreviated) or 0) > 0 and not screen.has_benefit(p.name_abbreviated)
            # The member-insurance gate belongs to the FALLBACK only. It's deliberately
            # coarser than the results page (hides where the page reduces the value), so
            # applying it on top of an authoritative client list would drop a program
            # the user is looking at — the MFB-1427 failure in reverse.
            and (visible is not None or not _has_member_insurance(screen, p.name_abbreviated))
            and (visible is None or p.name_abbreviated in visible)
        ]

        # A client list that matches nothing is malformed input, not an empty results
        # page — same reasoning as `_visible_programs`' own all-junk guard. Without
        # this, `visible_programs: ["zzz"]` empties the list, and ai-service then
        # renders "this person has NO eligible programs" and persists it. An
        # explicitly empty list still means "showing nothing" and is left alone.
        if visible and not rows and any(p.eligible for p in all_rows):
            logger.warning(
                "visible_programs for screen %s matched no eligible snapshot rows (%s); "
                "falling back to the server-side filters",
                screen.uuid,
                sorted(visible)[:10],
            )
            rows = [
                p
                for p in all_rows
                if p.eligible
                and (values.get(p.name_abbreviated) or 0) > 0
                and not screen.has_benefit(p.name_abbreviated)
                and not _has_member_insurance(screen, p.name_abbreviated)
            ]

        # Sort by what the user sees, so "your biggest one" agrees with their screen.
        rows.sort(key=lambda p: values.get(p.name_abbreviated) or 0, reverse=True)
        apply_urls = _apply_urls_by_name(screen, [p.name_abbreviated for p in rows])
        for p in rows:
            # The snapshot's `name` was captured as `program.name.text` under whatever
            # language was active when eligibility ran (screener.views, unpinned), and
            # non-default translation rows are created with text="". So a snapshot
            # computed under a non-English request can hold "" or the placeholder —
            # which would render as "- (wa_snap)" in the prompt. Same fallback as
            # _current_programs.
            snapshot_name = " ".join((p.name or "").split())[:MAX_PROMPT_FIELD_LEN]
            if snapshot_name == BLANK_TRANSLATION_PLACEHOLDER:
                snapshot_name = ""
            program = {
                "external_name": p.name_abbreviated,
                "name": snapshot_name or p.name_abbreviated,
                # Whole dollars. Frequency is governed by value_type; see the
                # API contract's open question on units.
                "estimated_value": values.get(p.name_abbreviated),
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
        # rstrip: FRONTEND_DOMAIN is env-supplied and a trailing slash would emit "//".
        "results_url": (
            f"{settings.FRONTEND_DOMAIN.rstrip('/')}/{screen.white_label.code}/{screen.uuid}/results/benefits"
        ),
    }


def _visible_programs(body: dict) -> Optional[list[dict]]:
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
    raw = body.get("visible_programs")
    if not isinstance(raw, list):
        return None
    if len(raw) > MAX_VISIBLE_PROGRAMS:
        # Truncation can only *hide* real programs (the list narrows), so make it
        # visible rather than silent — `_write_current_benefits` sets the same
        # precedent for dropped names.
        capture_message(
            f"visible_programs exceeded {MAX_VISIBLE_PROGRAMS} entries ({len(raw)}); truncating",
            level="warning",
        )

    programs: list[dict] = []
    seen: set[str] = set()
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
        normalized = name.strip().lower()
        # First wins. Building the lookup dict in _build_context would otherwise be
        # last-wins, letting a caller send the same program twice to choose which
        # `value` applies.
        if normalized in seen:
            continue
        seen.add(normalized)
        programs.append({"name_abbreviated": normalized, "value": _clean_value(value)})

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


class AssistantStartRateThrottle(HashedIPAnonRateThrottle):
    scope = "assistant_start"


class AssistantMessageRateThrottle(HashedIPAnonRateThrottle):
    scope = "assistant_message"


def _body(request) -> dict:
    """The request body as a dict.

    `request.data` is a list for a JSON array body and a QueryDict for a form post, so
    `.get` is not safe to assume — an array body would 500 rather than being ignored.
    """
    return request.data if isinstance(request.data, dict) else {}


class AssistantStartView(views.APIView):
    """POST: open (or resume) a Benbot conversation for a screen."""

    permission_classes = [permissions.AllowAny]
    # AllowAny + a proxy to a paid LLM: same shape as the REM/Places proxies, which
    # are throttled for the same reason. A start call also persists context in
    # ai-service, so it isn't only a cost concern.
    throttle_classes = [AssistantStartRateThrottle]

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

        body = _body(request)
        payload = {
            "screen_uuid": str(screen.uuid),
            "white_label": screen.white_label.code,
            "locale": body.get("locale", "en-US"),
            "context": _build_context(screen, _visible_programs(body)),
        }
        return _proxy("POST", "/v1/conversations", payload)


class AssistantMessageView(views.APIView):
    """POST: send a user message to an existing Benbot conversation."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AssistantMessageRateThrottle]

    def post(self, request, screen_uuid, conversation_id):
        screen = get_object_or_404(Screen, uuid=screen_uuid)
        if not screen.white_label.has_feature("benbot"):
            return Response({"error": {"code": "assistant_disabled"}}, status=status.HTTP_403_FORBIDDEN)

        body = _body(request)
        payload = {
            "text": body.get("text", ""),
            "client_message_id": body.get("client_message_id"),
        }
        return _proxy("POST", f"/v1/conversations/{conversation_id}/messages", payload)
