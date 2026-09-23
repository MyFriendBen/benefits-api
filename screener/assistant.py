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

import json
import logging
import os
import re
from typing import Optional

from urllib.parse import urlsplit

import phonenumbers
import requests
from django.conf import settings
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, views
from rest_framework.request import Request
from rest_framework.response import Response
from sentry_sdk import capture_message

from configuration.models import Configuration
from programs.framework.base import Eligibility
from programs.models import Document, Program, UrgentNeed, WarningMessage
from programs.util import Dependencies
from programs.warnings import warning_calculators
from programs.warnings.base import fill_warning_placeholders
from parler.models import TranslationDoesNotExist

from translations.models import BLANK_TRANSLATION_PLACEHOLDER, Translation

from .models import AssistantMessage, EligibilitySnapshot, ProgramEligibilitySnapshot, Screen
from .urgent_needs import eligible_urgent_needs
from .throttles import (
    AssistantHistoryRateThrottle,
    AssistantMessageRateThrottle,
    AssistantRatingRateThrottle,
    AssistantStartRateThrottle,
)

logger = logging.getLogger(__name__)

# Keys already reported by `_report_once`, for the life of the process.
_REPORTED: set[str] = set()

# Where mfb-ai-service lives, and the shared service token (must match the
# service's SERVICE_AUTH_TOKEN). Both come from the environment.
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8080")
AI_SERVICE_TOKEN = os.getenv("AI_SERVICE_TOKEN", "")
# 25s, not 60: Heroku's router terminates any request at 30 seconds and nothing in this
# path streams, so a 60s budget was unreachable — the browser got an H12 HTML page rather
# than the JSON error shape the widget handles, while this worker stayed blocked on a
# request no one was waiting for. 25 leaves room to return our own 502 first.
AI_SERVICE_TIMEOUT = 25

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

# The same cap for fields that are sentences rather than labels: document lines and
# warning messages. 160 is sized for a program name and clips real copy mid-sentence —
# tx_lifeline's warning ("...you should enroll in SNAP before applying for Lifeline")
# would lose the instruction that makes it worth sending. Still bounded, for the same
# prompt-injection reason MAX_PROMPT_FIELD_LEN exists.
#
# 800 rather than 400 because 400 was already clipping production: the longest live
# warning we actually forward is 562 chars (cccap_jeffco, CO), and the seed configs
# hold warnings up to 706. Documents top out at 338. A clipped warning is the failure
# `_apply_url` refuses for links — a half-sentence instruction delivered with full
# authority — so anything that does hit this is reported rather than silently cut.
MAX_PROMPT_TEXT_LEN = 800

# Per-program ceilings on those lists, so a misconfigured program can't crowd out the
# rest of the prompt. Same role as MAX_VISIBLE_PROGRAMS.
#
# Sized against production, NOT the seed configs — most of this data is created through
# the Django admin and never appears in a *_initial_config.json. As of 2026-09-10 the
# real maxima are 16 documents on one program (mo_tanf, MO) and 5 warnings on one.
# These must stay above those: truncating a checklist would break the parity with the
# results page that this feature exists to provide, and it would do it silently, on
# whichever program happens to have the most documents. Headroom is deliberate — the
# document count grows whenever a program's config is revised.
#
# There is deliberately no cap on programs x documents. The absolute ceiling, measured
# against production, is a household eligible for every active program in the largest
# white label: 43 programs, 207 document lines, ~13,000 characters (~3,300 tokens). A
# total budget that dropped lines past a threshold would buy a smaller worst case at the
# price of silently handing someone a short checklist — the same failure this file just
# fixed by raising the per-program cap, and the one thing the results-page parity in
# MFB-1788 cannot tolerate. If the budget ever needs enforcing, the honest lever is
# fewer programs in the prompt (inject on demand), not fewer documents per program.
MAX_DOCUMENTS_PER_PROGRAM = 24
MAX_WARNINGS_PER_PROGRAM = 10

# Apply links are dropped rather than truncated past this, so it's a reject threshold
# and not a clip point. Comfortably above the longest link in the seed config (~200).
MAX_URL_LEN = 500

# Ceiling on the additional-resources list. Sized above the real maximum for the same
# reason as MAX_DOCUMENTS_PER_PROGRAM: as of 2026-09-17 the largest white label has 43
# active resources in total (MO), so even a household that ticked every category on the
# immediate-needs step stays inside this. Truncating would silently break the parity with
# the Additional Resources tab that this list exists to provide, so hitting it is
# reported rather than quietly absorbed.
MAX_ADDITIONAL_RESOURCES = 60

# `acute_condition_options` config key -> the `Screen` field it writes. This mirrors
# `benefits-calculator/src/Assets/updateScreen.ts`, which is where the mapping has lived
# alone until now — the browser translates the step's answers into these columns, and the
# API only ever sees the columns.
#
# It is here because Benji may tell someone which category to ADD, and the categories a
# white label actually offers are config, not code: CO offers 11 of these, TX 12, and
# "funeral" is a category the resource table has but no white label offers at all. Naming
# a category that isn't on their step is the same fabrication as naming a button that
# isn't on their page, so the offered set has to be read from the same config the step
# renders from.
#
# `test_assistant_context.py` asserts every key in every white label's live config
# resolves to a real Screen field, so a new category added to the config without a column
# fails a test instead of silently vanishing from Benji's suggestions.
ACUTE_OPTION_FIELDS = {
    "food": "needs_food",
    "babySupplies": "needs_baby_supplies",
    "housing": "needs_housing_help",
    "support": "needs_mental_health_help",
    "childDevelopment": "needs_child_dev_help",
    "familyPlanning": "needs_family_planning_help",
    "jobResources": "needs_job_resources",
    "dentalCare": "needs_dental_care",
    "legalServices": "needs_legal_services",
    "savings": "needs_college_savings",
    "veteranServices": "needs_veteran_services",
    "disabilityResources": "needs_disability_resources",
    "agingResources": "needs_aging_resources",
    "homelessServices": "needs_homeless_services",
    "freeLowCostMedicalCare": "needs_free_low_cost_medical_care",
    "transportation": "needs_transportation",
    "medicalExpensesAndDebt": "needs_medical_expenses_and_debt",
}

# Program names that look like member-level insurance, used only to report a config
# gap loudly (see _insurance_program_names).
_LOOKS_LIKE_INSURANCE = re.compile(r"medicaid|chip|medicare|mass_health|apple_health")

# Relations _build_context reads per program or per member, so without these the query
# count grows with the number of eligible programs or household members:
#   current_benefits__program -> screen.has_benefit(), and screen.has_base_benefit()
#       from the co_snap_student warning calculator
#   household_members__insurance -> screen.has_insurance_types() (and the reverse
#       OneToOne `member.insurance`, which hasattr() would otherwise query per member)
# The rest are what screen.missing_fields() walks to build the Dependencies set the
# warning calculators gate on (see _warning_messages). Each is a reverse relation that
# `hasattr`/`.all()` would otherwise hit once per member or per call.
#
# This list is NOT the whole story, and adding to it is not always the fix: the warning
# calculators themselves read further than missing_fields() does. `_tax_unit` reaches
# Screen.has_members_outside_of_tax_unit -> is_dependent -> get_reference_date, whose
# `validations.order_by(...)` builds a fresh queryset and so cannot be prefetched from
# here at all — that one is solved by memoizing on the model. If a new calculator
# regresses the query count, check what it reads before reaching for this tuple.
CONTEXT_PREFETCH = (
    "current_benefits__program",
    "household_members__insurance",
    "household_members__income_streams",
    "household_members__energy_calculator",
    "expenses",
    "energy_calculator",
)


def _ai_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if AI_SERVICE_TOKEN:
        headers["Authorization"] = f"Bearer {AI_SERVICE_TOKEN}"
    return headers


def _report_once(key: str, message: str, *, level: str = "warning") -> None:
    """Report a config-level condition once per process rather than once per request.

    These conditions are properties of the configuration, not of the request: an
    unregistered calculator, a calculator the snapshot cannot satisfy, a warning too
    long for the prompt. They are unchanging until someone edits the admin, but they are
    evaluated inside a per-program, per-warning loop on every assistant start — so
    reporting them per request turns one static fact into the highest-volume event this
    module emits, and buries the ones that are actionable.

    Deduping in-process (not globally) is deliberate: a fresh dyno re-reports, so the
    signal survives a deploy and cannot be permanently silenced by one early request.
    """
    if key in _REPORTED:
        return
    _REPORTED.add(key)
    if level == "info":
        logger.info(message)
    else:
        capture_message(message, level=level)


def _clipped(text: str, what: str) -> str:
    """Bound a document line or warning message, reporting rather than silently cutting.

    Truncation here is not cosmetic: these are instructions ("enroll in SNAP before
    applying for Lifeline"), and half of one is the same class of failure `_apply_url`
    refuses for links — authoritative-looking and wrong. The text is still clipped
    rather than dropped, because most of a checklist item is worth more than none of it,
    but the condition is a config problem someone should fix, so it is reported.

    Resolves at full length (`max_len=None`) so the check sees the real length; going
    through `_translated`'s own cap would make over-long text indistinguishable from
    text that happens to end at the limit.
    """
    if len(text) <= MAX_PROMPT_TEXT_LEN:
        return text
    _report_once(
        f"clipped:{what}",
        f"Clipping {what} for the assistant: {len(text)} chars exceeds " f"MAX_PROMPT_TEXT_LEN={MAX_PROMPT_TEXT_LEN}",
    )
    return text[:MAX_PROMPT_TEXT_LEN]


def _translated(
    translation: Optional[Translation],
    language_code: Optional[str] = None,
    max_len: Optional[int] = MAX_PROMPT_FIELD_LEN,
) -> str:
    """Resolve a parler Translation to text, or "" if there isn't any usable text.

    Tries `language_code`, then falls back to `settings.LANGUAGE_CODE`. The fallback is
    necessary because non-default rows are created with `text=""`
    (`translations.models.add_translation`), and because the row *exists* parler's
    `hide_untranslated` never fires — so reading `.text` under a Spanish request would
    yield empty strings rather than the English name.

    Trying the requested language *first* matters for `apply_button_link`, where the
    non-English row is often legitimately different (state portals have /es landing
    pages). Pinning straight to LANGUAGE_CODE served everyone the English URL.

    `max_len=None` disables truncation. Names are capped because they're interpolated
    into ai-service's *system* prompt and `Translation` rows are admin-editable, so a
    name carrying newlines plus instruction-shaped text could forge a prompt block. URLs
    must NOT be capped — see `_apply_url`.
    """
    if translation is None:
        return ""
    for lang in (language_code, settings.LANGUAGE_CODE):
        if not lang:
            continue
        try:
            translation.set_current_language(lang)
            text = (translation.text or "").strip()
        except TranslationDoesNotExist:
            # No row for this language at all. `hide_untranslated=True` means parler
            # won't fall back for us, so try the next language rather than giving up —
            # returning here skipped the LANGUAGE_CODE fallback entirely, which is the
            # whole point of the loop.
            continue
        except AttributeError:
            # Genuinely not a translation object. Deliberately narrow: a bare
            # `except Exception` would swallow OperationalError and silently degrade
            # every name in the payload.
            return ""
        if text and text != BLANK_TRANSLATION_PLACEHOLDER:
            flattened = " ".join(text.split())
            return flattened[:max_len] if max_len else flattened
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


def _documents_prefetch() -> Prefetch:
    """Prefetch each program's documents with their text translation resolved.

    `select_related("text")` on the inner queryset folds the Translation parent into
    the document fetch, the way `select_related("apply_button_link")` does for the FK
    that hangs directly off Program — a plain "documents__text__translations" string
    costs an extra query for that hop.
    """
    return Prefetch(
        "documents",
        queryset=(Document.objects.select_related("text").prefetch_related("text__translations").order_by("id")),
    )


def _context_programs(screen: Screen, name_abbreviations: list[str]) -> dict[str, Program]:
    """Map name_abbreviated -> Program for the rows _build_context annotates (one query).

    Apply links, documents and warnings all hang off the same `Program` rows for the same
    name set, so they share one fetch rather than issuing three identical
    `name_abbreviated__in` queries.

    Only the translations we actually render are prefetched. `Document` and
    `WarningMessage` each also carry `link_url` and `link_text`, and the prompt's LINKS
    rule is absolute: apply links are the only URLs the assistant may share. Fetching
    just `text`/`message` means a document or warning URL is never loaded into the
    process at all, so it cannot reach the prompt through a later edit here — structural
    rather than a promise. (`Document.objects.translated_fields` would pull all three.)
    """
    if not name_abbreviations:
        return {}

    programs = (
        Program.objects.filter(
            white_label=screen.white_label,
            name_abbreviated__in=name_abbreviations,
        )
        .select_related("apply_button_link")
        .prefetch_related(
            "apply_button_link__translations",
            _documents_prefetch(),
            Prefetch(
                "warning_messages",
                queryset=(
                    WarningMessage.objects.select_related("message")
                    .prefetch_related("message__translations")
                    .order_by("id")
                ),
            ),
            "warning_messages__counties",
            "warning_messages__legal_statuses",
        )
    )
    return {program.name_abbreviated: program for program in programs}


def _apply_url(program: Program, language_code: str) -> str:
    """This program's apply link, or "" if there isn't a usable one.

    apply_button_link is a translated field, resolved through `_translated` so
    blank/placeholder links come back empty — the assistant must never receive an empty
    or placeholder URL, since it's instructed to treat the links it's given as the only
    ones it may share.

    URLs are **validated, not truncated.** The prompt orders the model to copy apply
    links character-for-character, so a clipped link is an authoritative-looking 404 and
    strictly worse than the designed "I don't have a direct link" fallback. Two links in
    the current seed config already exceed the name cap (tx_wic at 198 chars, il_ibccp at
    174), so truncating here would have shipped two dead links.
    """
    link = _translated(program.apply_button_link, language_code, max_len=None)
    if not link:
        return ""
    if len(link) > MAX_URL_LEN:
        capture_message(
            f"Dropping {program.name_abbreviated} apply link: {len(link)} chars exceeds MAX_URL_LEN={MAX_URL_LEN}",
            level="warning",
        )
        return ""
    return link


def _document_texts(program: Program, language_code: str) -> list[str]:
    """The documents the results page lists for this program.

    Static per program — no household gating, unlike warnings — so these are read
    straight off `Program` with no reconstruction.

    Ordered explicitly by id, matching the `order_by` added to the results page's own
    prefetch in `screener.views`. Neither `Document` nor the auto-created M2M declares
    an ordering, and Postgres guarantees no row order between two separate queries
    against the same join table — so "the default order" was not a shared order at all,
    and the checklist could read back in a different sequence from the "more info"
    panel beside it. Both sides now sort the same way by construction.
    """
    texts = []
    for document in program.documents.all():
        # Blank and [PLACEHOLDER] rows come back "" — an untranslated document is
        # dropped rather than rendered as an empty checklist line.
        text = _clipped(
            _translated(document.text, language_code, max_len=None),
            f"document {document.external_name or document.id} on {program.name_abbreviated}",
        )
        if text:
            texts.append(text)
    return texts[:MAX_DOCUMENTS_PER_PROGRAM]


def _warning_messages(
    program: Program,
    screen: Screen,
    eligible: bool,
    missing_dependencies: Dependencies,
    language_code: str,
) -> list[str]:
    """The warning messages this household would see on this program's results panel.

    Warnings are not a static field: each is evaluated per household by a calculator in
    `programs/warnings/`, gated on county, on missing screen fields, and on custom
    `eligible()` logic. `screener.views.eligibility_results` runs that evaluation inline
    and does NOT persist the result, so there is nothing on the snapshot to read.

    Rather than add a snapshot column, we re-run the gates here. That's cheap because
    nearly every registered calculator needs only `screen` — county, member data,
    `energy_calculator`, `num_adults` — or the program itself (`_prior_tax_year` reads
    its configured year). `screen.missing_fields()` is pure screen data (no
    PolicyEngine), and `Eligibility()` takes no constructor args, so the only input we
    cannot reproduce is `eligible_members`, which no snapshot stores. Calculators that
    read it declare `needs_full_eligibility` and are skipped loudly below.

    Because the gates read the screen as it is *now* while the program list comes from
    the last snapshot, a screen edited since that run could yield warnings the results
    page didn't show. In practice the results page recomputes eligibility on load, so
    the snapshot is fresh — the same premise `_latest_snapshot` rests on — and every
    gate input is screen-side, so an unchanged screen gives the run's own answer.

    Two deliberate divergences from the results-page evaluation:

    1. Warnings carrying `legal_statuses` are dropped. The results page filters those
       client-side against the citizenship dropdown (Results/ProgramPage.tsx), which
       defaults to 'citizen' and is never persisted to the Screen — so we cannot
       reproduce the selection, and we won't take it from the payload for the same
       reason `_visible_programs` is limited to names. All six such warnings in the seed
       config are immigration-status-scoped and none lists 'citizen', so none of them
       render on a default results page anyway. Under-reporting here is the safe
       direction: it never surfaces immigration-status content to a household that
       didn't ask for it.
    2. An unknown calculator name is skipped, where the eligibility run raises. A config
       typo should not take the assistant down with it.
    """
    warnings = program.warning_messages.all()
    if not warnings:
        return []

    # The minimum the gates read. Nothing consults pass_messages/fail_messages, so the
    # snapshot's failed_tests/passed_tests (stored as JSON *strings*, not lists) are
    # left alone rather than parsed back.
    eligibility = Eligibility()
    eligibility.eligible = eligible

    messages = []
    for warning in warnings:
        calculator = warning_calculators.get(warning.calculator)
        if calculator is None:
            _report_once(
                f"unknown-calculator:{warning.calculator}",
                f"Skipping warning {warning.external_name or warning.id} on "
                f"{program.name_abbreviated}: '{warning.calculator}' is not a valid calculator name",
            )
            continue
        if calculator.needs_full_eligibility:
            # A documented, accepted limitation rather than an incident, so it goes to
            # the log and not to Sentry — see `_report_once`.
            _report_once(
                f"needs-full-eligibility:{warning.calculator}",
                f"Skipping warning {warning.external_name or warning.id} on "
                f"{program.name_abbreviated} for the assistant: '{warning.calculator}' needs "
                "member-level eligibility, which the snapshot does not store",
                level="info",
            )
            continue
        if warning.legal_statuses.all():
            continue

        if not calculator(screen, warning, eligibility, missing_dependencies, program=program).calc():
            continue

        message = _clipped(
            fill_warning_placeholders(
                _translated(warning.message, language_code, max_len=None), screen.get_reference_date()
            ),
            f"warning {warning.external_name or warning.id} on {program.name_abbreviated}",
        )
        if message:
            messages.append(message)

    return messages[:MAX_WARNINGS_PER_PROGRAM]


def _insurance_program_names(screen: Screen) -> set[str]:
    """`name_abbreviated`s of this white label's programs the household holds via the
    member-level Insurance system.

    Resolves each program two ways, because `insurance_map()`'s keys are a mix of generic
    names and specific white-label ones:

      1. exact `name_abbreviated` match  (`co_medicaid`, `wa_apple_health_medicaid`)
      2. `base_program` match            (`ks_medicaid` -> base_program `medicaid`)

    The `base_program` arm is what makes this generic rather than a hand-maintained list —
    it's the same structural grouping `has_base_benefit` reads, so a new state variant is
    covered as soon as its `base_program` is set.

    Programs that resolve neither way are reported to Sentry rather than silently
    mishandled: for those, an already-enrolled household still gets the program
    recommended (the MFB-1427 bug) *and* it's missing from `current_programs`. Several
    exist today (the `tx_medicaid_for_*` family, `tx_chip`, and the `*_emergency_medicaid`
    pair have no `base_program`), and the fix is config, not code.
    """
    held_keys = screen.held_insurance_keys()
    if not held_keys:
        return set()

    rows = Program.objects.filter(white_label=screen.white_label).values_list("name_abbreviated", "base_program")
    held_names: set[str] = set()
    unmapped: list[str] = []
    for name, base_program in rows:
        if name in held_keys or (base_program and base_program in held_keys):
            held_names.add(name)
        elif _LOOKS_LIKE_INSURANCE.search(name) and not base_program:
            unmapped.append(name)

    if unmapped:
        capture_message(
            "Programs look like member-level insurance but map to no insurance_map key or "
            f"base_program, so enrollment can't be detected for them: {sorted(unmapped)}",
            level="warning",
        )
    return held_names


def _current_programs(screen: Screen, language_code: str) -> list[dict]:
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
    the insurance gate AND absent here, so ai-service's closed-world rule would
    forbid the assistant from naming it at all — "why did my Medicaid renewal letter
    arrive?" would get a refusal.

    Deliberately carries no estimated_value (the screening estimates what they
    *would* get, which is misleading for a benefit already in payment) and no
    apply_url (the assistant must never send them to apply again).

    Documents ARE included: recertification needs them too ("what do I need to renew
    my SNAP"), and a document list is neither of the two things this shape is thin to
    avoid. Warnings are not — they're application caveats evaluated for programs the
    household is being told to apply for, and this list is the opposite of that.
    """
    # One joined query through the CurrentBenefit table (unioned with the
    # insurance-derived names), plus one prefetch for the translation rows. `name` is
    # an FK to Translation, but Translation is a parler TranslatableModel whose text
    # lives in a separate table — so select_related alone still resolves `.text` per
    # row. `currentbenefit` is the default reverse accessor; CurrentBenefit.program
    # declares no related_name.
    #
    # White-label scoped like its sibling _context_programs: the write path in
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
        .distinct().select_related("name")
        # Documents ride this query rather than a second one — same rows, and
        # `_document_texts` needs nothing else. Text only, no link translations, for
        # the reason in `_context_programs`.
        .prefetch_related("name__translations", _documents_prefetch())
    )

    current = []
    for program in programs:
        entry = {
            "external_name": program.name_abbreviated,
            # Fall back to the abbreviation so the assistant can still name the
            # program when the translation is missing or blank.
            "name": _translated(program.name, language_code) or program.name_abbreviated,
        }
        documents = _document_texts(program, language_code)
        if documents:
            entry["documents"] = documents
        current.append(entry)

    # casefold, because names that fell back to `name_abbreviated` are lowercase and
    # would otherwise all sort after every translated name.
    current.sort(key=lambda p: p["name"].casefold())
    return current


def _is_shareable_url(url: str) -> bool:
    """An absolute http(s) URL with an actual host.

    The scheme prefix alone is not enough, and `"https://"` is the case that proves it:
    it passes a `startswith` check and reaches the model as a link it is told to
    reproduce character-for-character, which the widget then renders as a clickable
    href that goes nowhere. A link that cannot be opened is the same failure as a
    truncated one — an authoritative-looking dead end — and the designed fallback
    ("the link is on your results page") is strictly better.

    `urlsplit` rather than a regex: it is the parser the value will actually be read
    by, and it treats userinfo, ports and IPv6 literals the way a browser does.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.hostname)


def _resource_url(need: UrgentNeed, language_code: str) -> str:
    """This resource's website, or "" if there isn't a usable one.

    Validated rather than truncated, exactly like `_apply_url`: the prompt instructs the
    model to copy the links it is given character-for-character, so a clipped URL becomes
    an authoritative-looking 404 and is strictly worse than saying nothing. `link` is a
    `no_auto` translated field, so a blank or placeholder row comes back "" and the
    resource simply ships without a link.

    Must be an absolute http(s) URL. `Translation.text` holds arbitrary admin-editable
    text, and this value is handed to the model as something to reproduce verbatim and
    is rendered as a clickable link in the chat widget — so a `javascript:` or `data:`
    value would be an editable-row path to an attacker-controlled href, and a plain-text
    value ("call them") would be emitted as a broken link. Every one of the 273 live
    resource links is already http(s), so this rejects nothing real; it closes the shape
    of the field rather than fixing a present-day row.
    """
    link = _translated(need.link, language_code, max_len=None)
    if not link:
        return ""
    if not _is_shareable_url(link):
        _report_once(
            f"non_http_resource_link:{need.external_name or need.id}",
            f"Dropping resource {need.external_name or need.id} link: not an absolute http(s) URL with a host",
        )
        return ""
    if len(link) > MAX_URL_LEN:
        capture_message(
            f"Dropping resource {need.external_name or need.id} link: {len(link)} chars exceeds "
            f"MAX_URL_LEN={MAX_URL_LEN}",
            level="warning",
        )
        return ""
    return link


def _resource_phone(need: UrgentNeed) -> str:
    """The resource's phone number in the same format the card shows it.

    `PhoneNumberField` stores E.164 (+13035551234); the resource card renders
    `formatNational()` ("(303) 555-1234"). Benji is told these numbers are the only ones
    it may ever say out loud, so it should say them the way the page prints them —
    someone reading the card and someone asking Benji must not get two different-looking
    numbers for the same organization.

    The validity check mirrors the card's, and is not decoration. `formatPhoneNumber`
    in the frontend formats only when `isValid()` and otherwise prints the stored string
    unchanged, so an invalid-but-stored number (a extension-only entry, a number saved
    before validation tightened) shows raw on the card. `format_number` does NOT raise on
    those — it returns a plausible-looking reformat — so without this, the one field this
    change claims parity for would be the one field where Benji and the card disagree,
    and only for the rows most likely to be wrong already.
    """
    number = need.phone_number
    if not number:
        return ""
    try:
        if not phonenumbers.is_valid_number(number):
            return str(number)
        return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.NATIONAL)
    except Exception:
        # A stored number that the library won't format is a config problem, not a reason
        # to fail the turn. Dropping it costs a contact route; emitting something
        # malformed would have Benji read out digits that don't dial.
        _report_once(
            f"unformattable_phone:{need.external_name or need.id}",
            f"Dropping an unformattable phone number on resource {need.external_name or need.id}",
        )
        return ""


# How the household reaches the Immediate Help resources (2-1-1 and the like).
#
# Four shapes, not one, which is why this is computed per screen rather than described
# once in the prompt: see `_immediate_help`.
IMMEDIATE_HELP_TAB = "tab"
IMMEDIATE_HELP_BUTTON = "button"
IMMEDIATE_HELP_ABSENT = "absent"

# Ceiling on the Immediate Help list. Sized well above reality — the largest configured
# `more_help_options` holds a handful of entries (most tenants have exactly one, a 2-1-1
# line) — and exists for the same reason as the other caps: to bound a list that reaches
# the system prompt.
MAX_IMMEDIATE_HELP_RESOURCES = 16

# A referrer carrying this in its `uiOptions` hides the Immediate Help route entirely.
# Per REFERRER, not per white label: NC sets it on 211nc, hfed, lanc and ccla but not on
# its default, so two households on the same white label genuinely see different pages.
NO_IMMEDIATE_HELP_UI_OPTION = "no_results_more_help"

# The one white label that renders no tab bar at all. Its Immediate Help resources live
# on a standalone page reached from a button (`211Button.tsx`: "CESN renders no tab bar,
# so this is its only entry point to that page").
NO_TAB_BAR_WHITE_LABEL = "cesn"


def _config_data(screen: Screen, *names: str) -> dict[str, dict]:
    """Several of a white label's `Configuration.data` payloads, decoded, in ONE query.

    Takes a list rather than a single name because `_immediate_help` needs two
    (`more_help_options` and `referrer_data`) and the start endpoint's query count is
    bounded by a test that is deliberately hard to raise — two lookups where one will do
    is exactly what that bound exists to catch.

    `Configuration.data` comes back as a JSON *string*, not a dict: `OrderedJSONField`
    json.dumps() on the way in and the column then encodes that string as jsonb, so one
    decode leaves the payload still encoded. Both shapes are accepted because the field
    would start returning dicts the day that double-encoding is fixed.

    Names with no active row, or with unparseable data, are simply absent from the
    result — every caller here treats a missing config as "this tenant offers nothing",
    which is the safe reading.
    """
    out: dict[str, dict] = {}
    rows = Configuration.objects.filter(white_label=screen.white_label, name__in=names, active=True).values_list(
        "name", "data"
    )
    for name, data in rows:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                _report_once(
                    f"unparseable_config:{screen.white_label.code}:{name}",
                    f"{name} for {screen.white_label.code} is not valid JSON; the assistant cannot use it",
                )
                continue
        if isinstance(data, dict):
            out[name] = data
    return out


def _immediate_help_entry_point(screen: Screen, referrer_data: dict, has_resources: bool) -> str:
    """Whether this household sees Immediate Help as a tab, a button, or not at all.

    THE RESULTS PAGE IS NOT ONE SHAPE, which is the whole reason this is in the context
    rather than stated once in the prompt. `buildTabs.ts` adds the tab only when it is
    neither suppressed nor empty, and CESN renders no tab bar at all — so a prompt that
    asserted "three tabs" would be wrong for at least three different populations, and
    naming a tab that is not there is the same failure as inventing a button (MFB-1872).

    Suppression is read from the screen's OWN referrer, not the white label's default:
    NC turns it off for 211nc, hfed, lanc and ccla while leaving its default on.

    EMPTY BEATS CESN, and the order of these checks is the whole of it. An earlier
    version returned `button` for CESN whenever the route was not suppressed, including
    with nothing behind it — but `Results.tsx` redirects `results/more-help` back to the
    benefits list when there are no resources, and that branch runs BEFORE the CESN one
    ("Must run before the CESN branch below, so this redirects CESN too"). The button is
    still painted, so it looks like a route and is not one; telling Benji to point
    someone at it sends them in a circle.
    """
    if _immediate_help_suppressed(screen, referrer_data) or not has_resources:
        return IMMEDIATE_HELP_ABSENT
    # CESN renders no tab bar, so its route is the button on the results page.
    if screen.white_label.code == NO_TAB_BAR_WHITE_LABEL:
        return IMMEDIATE_HELP_BUTTON
    return IMMEDIATE_HELP_TAB


def _immediate_help_suppressed(screen: Screen, referrer_data: dict) -> bool:
    """Does this screen's referrer switch the Immediate Help route off?"""
    ui_options = referrer_data.get("uiOptions")
    if not isinstance(ui_options, dict):
        return False
    # `getReferrer` in the frontend falls back to "default" when the code has no entry.
    options = ui_options.get(screen.referrer_code) if screen.referrer_code else None
    if not isinstance(options, list):
        options = ui_options.get("default")
    return isinstance(options, list) and NO_IMMEDIATE_HELP_UI_OPTION in options


def _immediate_help(screen: Screen, language_code: str) -> dict:
    """The Immediate Help tab, as the assistant sees it.

    Deliberately a sibling of `additional_resources` rather than part of it. They are
    different things and the prompt must not blur them: additional resources are matched
    to what this household said they needed, while these are a fixed per-tenant list
    (2-1-1, state help lines) shown to everyone — so a count on them "would falsely
    imply personalization", which is exactly why the tab carries none.

    Name and phone are Translation-backed labels (`{_label, _default_message}`) resolved
    in the screen's language, because these are the words on the household's own screen.
    `link` is a plain config string, validated the same way `_resource_url` validates a
    resource link: absolute http(s) or dropped, never truncated.
    """
    configs = _config_data(screen, "more_help_options", "referrer_data")
    options = configs.get("more_help_options", {}).get("moreHelpOptions")
    if not isinstance(options, list):
        options = []

    labels = []
    for option in options:
        if not isinstance(option, dict):
            continue
        for key in ("name", "phone"):
            label = (option.get(key) or {}).get("_label") if isinstance(option.get(key), dict) else None
            if label:
                labels.append(label)
    rows = (
        {t.label: t for t in Translation.objects.filter(label__in=labels).prefetch_related("translations")}
        if labels
        else {}
    )

    def _text(option: dict, key: str) -> str:
        field = option.get(key)
        if not isinstance(field, dict):
            return ""
        text = _translated(row, language_code) if (row := rows.get(field.get("_label"))) else ""
        if text:
            return text
        # Fall back to the config's own English when the Translation gives us nothing —
        # whether because no row exists, or because a row exists and is BLANK.
        #
        # The blank case is not hypothetical: `add_translation` creates non-default rows
        # with `text=""`, and `add_translations --no-translate` writes blank rows on
        # purpose. `_translated` already falls back to LANGUAGE_CODE, so this only fires
        # when the default language is empty too — and then the `_default_message` sitting
        # right there in the config is better than dropping the entry, which is what an
        # `if row else` would do.
        #
        # Whitespace collapsed before the cap so the default takes the same shape a
        # translated value does; ai-service sanitizes again, but a name should not
        # depend on which branch produced it.
        return " ".join(str(field.get("_default_message") or "").split())[:MAX_PROMPT_FIELD_LEN]

    resources = []
    for option in options:
        if not isinstance(option, dict):
            continue
        name = _text(option, "name")
        if not name:
            # An unnamed entry is not something the assistant can offer anyone, and a
            # blank line in a list it is told is complete is worse than a shorter list.
            continue
        entry = {"name": name}
        # `contact`, not `phone_number`: the live value is "Dial 2-1-1", an instruction
        # rather than a dialable number, and it is translated per language. ai-service
        # sanitizes it as text for that reason.
        contact = _text(option, "phone")
        if contact:
            entry["contact"] = contact
        link = option.get("link")
        if isinstance(link, str) and link:
            if not _is_shareable_url(link):
                _report_once(
                    f"non_http_more_help_link:{screen.white_label.code}:{name}",
                    f"Dropping more_help link for {screen.white_label.code}/{name}: "
                    "not an absolute http(s) URL with a host",
                )
            elif len(link) > MAX_URL_LEN:
                _report_once(
                    f"long_more_help_link:{screen.white_label.code}:{name}",
                    f"Dropping more_help link for {screen.white_label.code}/{name}: over MAX_URL_LEN={MAX_URL_LEN}",
                )
            else:
                entry["link"] = link
        resources.append(entry)

    if len(resources) > MAX_IMMEDIATE_HELP_RESOURCES:
        capture_message(
            f"White label {screen.white_label.code} has {len(resources)} more_help options, over "
            f"MAX_IMMEDIATE_HELP_RESOURCES={MAX_IMMEDIATE_HELP_RESOURCES}; truncating the assistant's list",
            level="warning",
        )
        resources = resources[:MAX_IMMEDIATE_HELP_RESOURCES]

    # Deliberately the RAW option count, not `len(resources)`. The frontend's
    # `useImmediateHelpEmpty` tests `(moreHelpOptions ?? []).length`, before any name
    # resolution — so a tenant whose entries all resolve to empty names still gets the
    # tab on screen. Keying this off the filtered list would report "absent" while the
    # household is looking at the tab: the page-matching rule this function exists to
    # uphold, broken from the other side. When that happens the route is real and the
    # contents are not, and `_render_immediate_help` says exactly that.
    entry_point = _immediate_help_entry_point(screen, configs.get("referrer_data", {}), has_resources=bool(options))
    # No resources reach the model when there is no route to them: naming help the
    # household cannot get to on their screen is the closed-world break in reverse.
    return {
        "entry_point": entry_point,
        "resources": resources if entry_point != IMMEDIATE_HELP_ABSENT else [],
    }


def _additional_resources(
    screen: Screen,
    program_data: list[dict],
    missing_dependencies: Optional[Dependencies],
    language_code: str,
) -> list[dict]:
    """The Additional Resources tab, as the assistant sees it.

    Selected through `screener.urgent_needs.eligible_urgent_needs`, the same function the
    results page uses, so the two lists cannot drift — which matters because the prompt
    describes this one to the model in closed-world terms.

    Order comes from that same function and is NOT re-sorted here. An earlier version
    sorted by `(translated category, name)`, which quietly broke the parity it claimed:
    `Needs.tsx` sorts only by the ENGLISH category name and its sort is stable, so it
    preserves API order within a category, and on a non-English screen it orders the
    categories themselves differently from a translated key. "The first one on the list"
    named a different organization on each side. The shared function now owns the order.

    `warning` and `notification_message` are deliberately not forwarded. Neither appears
    on a resource card (`NeedCard.tsx` renders category, name, description, phone and
    link); the notification drives the banner on the *benefits* tab, and the warning is
    not rendered anywhere at all. Parity means what the card shows.
    """
    resources = []
    needs = eligible_urgent_needs(screen, program_data, missing_dependencies)

    for need in needs:
        name = _translated(need.name, language_code)
        if not name:
            # An unnamed resource is not something the assistant can offer anyone, and a
            # blank line in a list it's told is complete is worse than a shorter list.
            _report_once(
                f"unnamed_resource:{need.external_name or need.id}",
                f"Dropping resource {need.external_name or need.id} from the assistant context: no usable name",
            )
            continue

        entry = {
            # UrgentNeed.external_name is nullable and many rows have none, so fall back
            # to the pk. This is an opaque handle for logs and evals, not something the
            # model is asked to read out.
            "external_name": need.external_name or f"urgent_need_{need.id}",
            "name": name,
        }
        category = _translated(need.category_type.name, language_code) if need.category_type_id else ""
        if category:
            entry["category"] = category
        description = _clipped(
            _translated(need.description, language_code, max_len=None),
            f"description of resource {need.external_name or need.id}",
        )
        if description:
            entry["description"] = description
        phone = _resource_phone(need)
        if phone:
            entry["phone_number"] = phone
        link = _resource_url(need, language_code)
        if link:
            entry["link"] = link
        resources.append(entry)

    # The cap applies to an already-ordered list (`eligible_urgent_needs` sorts), so it
    # keeps the same head the results page shows rather than an arbitrary subset — above
    # the cap the two lists would otherwise differ in membership, not just in order.
    if len(resources) > MAX_ADDITIONAL_RESOURCES:
        capture_message(
            f"Screen {screen.uuid} has {len(resources)} additional resources, over "
            f"MAX_ADDITIONAL_RESOURCES={MAX_ADDITIONAL_RESOURCES}; truncating the assistant's list",
            level="warning",
        )
    return resources[:MAX_ADDITIONAL_RESOURCES]


def _unselected_need_categories(screen: Screen, language_code: str) -> list[str]:
    """Resource categories this white label offers that the household did NOT tick.

    The Additional Resources tab carries a link back to the immediate-needs step ("edit
    your selections in this step"), so a household that never ticked "food" has a real
    route to food resources — and Benji is allowed to point at it. That route is only
    safe to name if Benji knows which categories the step actually offers: the options
    are per-white-label config, and telling someone to pick one their step doesn't have
    is the same failure as inventing a button.

    Labels only. No counts, and no resource names: nothing here says whether that
    category has anything in it for this household's county, so the prompt has Benji
    offer it as "add it and I'll see what's there" rather than as a promise.
    """
    config = (
        Configuration.objects.filter(
            white_label=screen.white_label,
            name="acute_condition_options",
            active=True,
        )
        .values_list("data", flat=True)
        .first()
    )
    # `Configuration.data` comes back as a JSON *string*, not a dict. `OrderedJSONField`
    # json.dumps() on the way in and the column then encodes that string as jsonb, so one
    # decode leaves the payload still encoded — `configuration/admin.py` carries the same
    # `isinstance(..., str)` unwrap for the same reason. Both shapes are accepted here
    # because the field would start returning dicts the day that double-encoding is fixed,
    # and this feature should not be what breaks.
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except ValueError:
            _report_once(
                f"unparseable_acute_options:{screen.white_label.code}",
                f"acute_condition_options for {screen.white_label.code} is not valid JSON; "
                "the assistant cannot offer any resource categories",
            )
            return []
    if not isinstance(config, dict):
        return []

    labels: list[str] = []
    unknown: list[str] = []
    for key, option in config.items():
        field = ACUTE_OPTION_FIELDS.get(key)
        if field is None:
            unknown.append(key)
            continue
        if getattr(screen, field, False):
            continue
        label = ((option or {}).get("text") or {}).get("_label") if isinstance(option, dict) else None
        if label:
            labels.append(label)

    if unknown:
        _report_once(
            f"unmapped_acute_options:{screen.white_label.code}",
            f"acute_condition_options keys with no Screen field for {screen.white_label.code}: {sorted(unknown)}. "
            "Benji cannot offer these categories until ACUTE_OPTION_FIELDS covers them.",
        )
    if not labels:
        return []

    # One query for every label, then resolved in the screen's language like every other
    # user-facing string here — these are the exact words on the tiles they'd be clicking.
    rows = {t.label: t for t in Translation.objects.filter(label__in=labels).prefetch_related("translations")}
    names = [_translated(rows[label], language_code) for label in labels if label in rows]
    return sorted({name for name in names if name}, key=str.casefold)


def _displayed_value(row: ProgramEligibilitySnapshot, visible: Optional[dict[str, dict]]) -> Optional[int]:
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
    # The language the user chose in the app, NOT `get_language()` — that reflects the
    # browser's Accept-Language header under LocaleMiddleware, so an English MFB session
    # in a Spanish browser would get Spanish program names and Spanish /es apply links
    # while `payload["locale"]` said en-US. `get_language_code()` is what the results
    # email uses for the same reason.
    language_code = screen.get_language_code()

    eligible_programs = []
    # Shared with the additional-resources pass below, which runs whether or not there is
    # a snapshot — the resources tab does not depend on one.
    #
    # `missing_dependencies` is lazy because building it walks every member, expense and
    # income stream; both consumers below take it as an optional argument so it is built
    # at most once per request and only when something actually gates on it.
    program_data: list[dict] = []
    missing_dependencies: Optional[Dependencies] = None
    snapshot = _latest_snapshot(screen)
    if snapshot is not None:
        visible = {p["name_abbreviated"]: p for p in visible_programs} if visible_programs is not None else None
        all_rows = list(snapshot.program_snapshots.all())
        values = {p.name_abbreviated: _displayed_value(p, visible) for p in all_rows}

        # What the urgent-need calculators read out of the eligibility results. Five of
        # them gate a resource on program eligibility ("show SNAP application help if
        # they're SNAP-eligible"), and every one touches only these two keys — so the
        # snapshot reproduces it exactly, with no second call to PolicyEngine.
        #
        # Built from ALL rows, not the filtered `rows` below: a resource keyed on SNAP
        # eligibility must still appear for a household that already receives SNAP, and
        # that row is filtered out of `eligible_programs` precisely because they have it.
        program_data = [{"name_abbreviated": p.name_abbreviated, "eligible": p.eligible} for p in all_rows]

        insurance_held = _insurance_program_names(screen)

        def passes_server_gates(row: ProgramEligibilitySnapshot, *, apply_insurance_gate: bool) -> bool:
            """The gates we can reproduce from the snapshot.

            One definition rather than two comprehensions twenty lines apart: those had
            already drifted (the primary conditionalized the insurance gate, the fallback
            didn't) with no test comparing them.
            """
            return (
                row.eligible
                # The DISPLAYED figure, not the snapshot's — a client value of 0 would
                # otherwise slip a "~$0 per year" program in, exactly the row the results
                # page hides.
                and (values.get(row.name_abbreviated) or 0) > 0
                and not screen.has_benefit(row.name_abbreviated)
                and not (apply_insurance_gate and row.name_abbreviated in insurance_held)
            )

        # The insurance gate belongs to the FALLBACK only. It's deliberately coarser than
        # the results page (it hides where the page reduces the value), so applying it on
        # top of an authoritative client list would drop a program the user is looking at
        # — the MFB-1427 failure in reverse.
        rows = [
            p
            for p in all_rows
            if passes_server_gates(p, apply_insurance_gate=visible is None)
            and (visible is None or p.name_abbreviated in visible)
        ]

        # A client list whose names match no eligible row is malformed input, not an empty
        # results page — same reasoning as `_visible_programs`' own all-junk guard. Without
        # this, `visible_programs: ["zzz"]` empties the list and ai-service renders (and
        # persists) "this person has NO eligible programs".
        #
        # Tests the INTERSECTION, not `not rows`. Testing the outcome discarded a valid
        # client list whenever the server gates happened to empty it: the page is showing
        # only SNAP, the household toggles "I already receive SNAP" in another tab,
        # has_benefit drops it, and the fallback then replaced the list with every
        # server-filtered row *including the ones the page hid for legal status and
        # excludes_programs*. That is the failure the client list exists to prevent.
        if visible and not ({p.name_abbreviated for p in all_rows if p.eligible} & set(visible)):
            logger.warning(
                "visible_programs for screen %s matched no eligible snapshot rows (%s); "
                "falling back to the server-side filters",
                screen.uuid,
                sorted(visible)[:10],
            )
            rows = [p for p in all_rows if passes_server_gates(p, apply_insurance_gate=True)]

        # Sort by what the user sees, so "your biggest one" agrees with their screen.
        rows.sort(key=lambda p: values.get(p.name_abbreviated) or 0, reverse=True)
        programs_by_name = _context_programs(screen, [p.name_abbreviated for p in rows])
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
                # Whole dollars, annual. MFB-1019 (#1591) dropped `value_type`, which
                # used to govern frequency and left the units genuinely ambiguous; every
                # snapshot value is now an annual total, which is what ai-service's
                # prompt asserts.
                "estimated_value": values.get(p.name_abbreviated),
                "estimated_application_time": p.estimated_application_time,
                # Already on the snapshot and already sent to the results page; answers
                # "how long until I actually get this". Carries the same wart as
                # estimated_application_time — captured under whatever language was
                # active when eligibility ran.
                "estimated_delivery_time": p.estimated_delivery_time,
            }
            row_program = programs_by_name.get(p.name_abbreviated)
            if row_program is not None:
                apply_url = _apply_url(row_program, language_code)
                if apply_url:
                    program["apply_url"] = apply_url
                # Omitted rather than sent empty: ai-service defaults both to [], and
                # the prompt distinguishes "we have no list for this program" from
                # "this program needs nothing".
                documents = _document_texts(row_program, language_code)
                if documents:
                    program["documents"] = documents
                if row_program.warning_messages.all():
                    if missing_dependencies is None:
                        missing_dependencies = screen.missing_fields()
                    warnings = _warning_messages(row_program, screen, p.eligible, missing_dependencies, language_code)
                    if warnings:
                        program["warnings"] = warnings
            eligible_programs.append(program)

    # Disjointness is enforced HERE, not merely asserted. The insurance gate above is
    # skipped when the client sends a list (correctly — it's coarser than the page), but
    # the insurance union in `_current_programs` is unconditional, so a partially-enrolled
    # household could land the same program in both lists: "you may recommend
    # co_medicaid, apply here" alongside "they already receive co_medicaid", in one
    # payload. Eligible wins, because the page is showing it as available.
    eligible_names = {p["external_name"] for p in eligible_programs}
    current_programs = [p for p in _current_programs(screen, language_code) if p["external_name"] not in eligible_names]

    # Unconditional, and deliberately outside the `snapshot is not None` block: the
    # Additional Resources tab does not depend on an eligibility snapshot, so a screen
    # whose snapshot is missing or stale still has resources, and those may be the only
    # thing the assistant has to offer.
    additional_resources = _additional_resources(screen, program_data, missing_dependencies, language_code)

    return {
        "household": {"size": screen.household_size},
        "eligible_programs": eligible_programs,
        "current_programs": current_programs,
        # The other half of the results page. These are organizations to contact, not
        # benefits to apply for, and the prompt keeps that distinction — but they answer
        # the immediate "I can't feed my kids this week" that no long-term program does.
        "additional_resources": additional_resources,
        # The THIRD tab (MFB-824), and the one whose very existence varies: it is a tab
        # for most households, a button on CESN, and absent when the referrer suppresses
        # it or the tenant configured nothing. `entry_point` carries which, so the prompt
        # can describe the page this household is actually looking at instead of
        # asserting one shape for everyone.
        "immediate_help": _immediate_help(screen, language_code),
        # Only what this white label's immediate-needs step actually offers, minus what
        # they already ticked. Lets the assistant name the right category when someone
        # raises a need with no matching resources, instead of either staying silent or
        # inventing an option their step doesn't have.
        "unselected_need_categories": _unselected_need_categories(screen, language_code),
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


def _clean_value(value: object) -> Optional[int]:
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


def _proxy(method: str, path: str, json_body: dict = None, params: dict = None) -> Response:
    """Forward a request to mfb-ai-service and pass its response through.

    `json_body` for writes, `params` for reads — a GET with a JSON body is not
    something every intermediary handles predictably, and ai-service's read endpoint
    takes its screen id as a query parameter.
    """
    try:
        resp = requests.request(
            method,
            f"{AI_SERVICE_URL}{path}",
            json=json_body,
            params=params,
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


def _body(request: Request) -> dict:
    """The request body as a dict.

    `request.data` is a list for a JSON array body and a QueryDict for a form post, so
    `.get` is not safe to assume — an array body would 500 rather than being ignored.
    """
    return request.data if isinstance(request.data, dict) else {}


class AssistantStartView(views.APIView):
    """POST: open (or resume) a Benbot conversation for a screen.
    GET:  read an existing conversation back, creating nothing.

    Both live on one URL because they are the write and read halves of the same
    resource, but they are throttled separately — see `get_throttles`.

    WHAT THE GET EXPOSES, recorded as a decision rather than left implicit. Both verbs
    are AllowAny and the screen UUID is also the results-page URL, which we email to
    households — so anyone holding that link can read the full transcript, including
    whatever free text the household typed, which can be far more than the screener
    itself asks for. That exposure is not new: the POST has always returned `messages`
    for the same screen, and `_displayed_value` already documents the same "a third
    party who has seen a link" threat. The GET widens it in three specific ways worth
    naming:

      - it is silent — the POST mutates the stored context snapshot and creates a
        conversation, so repeated abuse leaves traces a read does not;
      - it is cheaper — 120/hour against the POST's 30;
      - it needs no request body.

    We are accepting that for now because the alternative is real per-household
    authentication, which this layer does not have (the frontend sends a shared API
    key, not a session) and which is a larger change than the storage work this
    endpoint belongs to. Rate limiting is NOT a mitigation here: one request is enough
    to read a transcript. If Benji ever carries more sensitive disclosure than it does
    today, this is the endpoint to put behind a real per-screen proof first.
    """

    permission_classes = [permissions.AllowAny]
    # AllowAny + a proxy to a paid LLM: same shape as the REM/Places proxies, which
    # are throttled for the same reason. A start call also persists context in
    # ai-service, so it isn't only a cost concern.
    throttle_classes = [AssistantStartRateThrottle]

    def get_throttles(self):
        """Per-method throttling.

        DRF applies `throttle_classes` to every method, which would put reads on the
        start budget (30/hour). The widget auto-opens on nearly every results page and
        a reload repeats the read, so ordinary browsing would exhaust a household's
        ability to actually open a conversation.

        HEAD counts as a read: Django's `View.setup` aliases it to the `get` handler
        when no `head` is defined, so a HEAD request is served by `get` below. Matching
        only "GET" charged it to the start budget instead — the exact inversion this
        override exists to prevent, and worse than it sounds because
        `HashedIPAnonRateThrottle` keys on the client IP, so one scanner or prefetcher
        would spend the budget for everyone behind that address.
        """
        if self.request.method in ("GET", "HEAD"):
            return [AssistantHistoryRateThrottle()]
        return super().get_throttles()

    def get(self, request, screen_uuid):
        """Return the household's existing conversation, or 404 if there isn't one.

        Exists so the chat widget can restore a transcript on open without writing
        anything. The POST below also resumes by screen, but it *creates* a
        conversation when there is none and refreshes the stored context snapshot when
        there is — so using it to restore history would mint an empty conversation for
        every visitor who opens the widget and never types.

        The 404 is an ordinary "no history yet", which is the common case, and the
        frontend treats it as such rather than as an error.
        """
        screen = get_object_or_404(Screen.objects.select_related("white_label"), uuid=screen_uuid)
        if not screen.white_label.has_feature("benbot"):
            return Response({"error": {"code": "assistant_disabled"}}, status=status.HTTP_403_FORBIDDEN)

        return _proxy("GET", "/v1/conversations", params={"screen_uuid": str(screen.uuid)})

    def post(self, request, screen_uuid):
        # CONTEXT_PREFETCH keeps _build_context's per-program enrollment checks on the
        # zero-query path. _current_programs still issues its own query — it needs the
        # translated names, which these prefetches don't carry.
        screen = get_object_or_404(
            Screen.objects.select_related("white_label").prefetch_related(*CONTEXT_PREFETCH),
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
            # `conversation_id` comes from the URL and was, on its own, enough to
            # continue ANY conversation from ANY screen: nothing tied it to the screen
            # the caller addressed. Because the benbot check above reads the CALLER's
            # white label, that also meant a white label with the flag off could still
            # have its conversations written and read through one that had it on —
            # defeating both a partial rollout and a per-white-label rollback.
            #
            # ai-service compares this against the conversation's stored screen_uuid and
            # answers 404 on a mismatch, so the pairing is enforced where the row lives.
            "screen_uuid": str(screen.uuid),
            "text": body.get("text", ""),
            "client_message_id": body.get("client_message_id"),
        }
        return _proxy("POST", f"/v1/conversations/{conversation_id}/messages", payload)


class AssistantMessageRatingView(views.APIView):
    """PUT: set, change, or clear the thumbs up/down on one assistant reply (MFB-1915).

    The one endpoint in this file that does NOT proxy to ai-service. Everything else
    here is a passthrough because the thing being asked for is a model completion or
    the transcript that ai-service assembles; a rating is neither. It is a scalar on a
    row whose schema this repo owns, needing no LLM, no `seq` assignment and no
    conversation row lock — so proxying it would put a second service and a second
    network hop in front of a single UPDATE, and take thumbs-up with it whenever
    ai-service is down even though the database is fine.

    ai-service still READS the column (it serves `GET /v1/conversations/{id}`, which is
    how a rating survives a page reload), so the two repos ship together. See the
    rating fields on `AssistantMessage` and `store_postgres._EXPECTED_COLUMNS`.

    One verb rather than three, because "rate", "change my rating" and "un-rate" are
    the same statement about the same message — `{"rating": 1 | -1 | null}` — and the
    widget toggles between them freely. PUT also makes the double-click that a slow
    network turns into two requests land on the same value instead of racing.

    PUT REPLACES BOTH FIELDS. The body states the whole feedback, so a call carrying
    `rating` and no `reason` clears any reason already stored. That is what makes
    picking a different chip, switching thumbs and un-rating all the same operation,
    and it is why the widget always sends the reason it wants kept rather than relying
    on the server to remember one.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AssistantRatingRateThrottle]

    VALID_RATINGS = (AssistantMessage.RATING_UP, AssistantMessage.RATING_DOWN)
    VALID_REASONS = frozenset(code for code, _ in AssistantMessage.RATING_REASON_CHOICES)

    def put(self, request, screen_uuid, conversation_id, message_id):
        screen = get_object_or_404(Screen.objects.select_related("white_label"), uuid=screen_uuid)
        if not screen.white_label.has_feature("benbot"):
            return Response({"error": {"code": "assistant_disabled"}}, status=status.HTTP_403_FORBIDDEN)

        body = _body(request)
        if "rating" not in body:
            return Response(
                {"error": {"code": "invalid_rating", "message": "A 'rating' key is required (1, -1 or null)."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rating = body["rating"]
        # `True == 1` in Python, so a JSON `true` would otherwise sail through the
        # membership test below and be stored as a thumbs up.
        if rating is not None and (isinstance(rating, bool) or rating not in self.VALID_RATINGS):
            return Response(
                {"error": {"code": "invalid_rating", "message": "rating must be 1, -1 or null."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # `reason` is optional in a way `rating` is not: the chips are offered AFTER the
        # thumbs-down is already saved, so most calls legitimately carry no reason at
        # all. Absent means "not answered" and is not an error.
        reason = body.get("reason")
        # `isinstance(reason, str)` before the membership test, not as belt-and-braces:
        # VALID_REASONS is a frozenset, and a JSON array or object body value is
        # unhashable, so `reason not in VALID_REASONS` raises TypeError and the caller
        # gets a 500 instead of the 400 this branch exists to produce. Same class of
        # trap as the `isinstance(rating, bool)` guard above.
        if reason is not None and (not isinstance(reason, str) or reason not in self.VALID_REASONS):
            return Response(
                {
                    "error": {
                        "code": "invalid_reason",
                        "message": f"reason must be null or one of: {', '.join(sorted(self.VALID_REASONS))}.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # A reason only means anything against a thumbs-down. Rejecting rather than
        # silently dropping it: a client sending one with a thumbs-up has a bug, and
        # swallowing it would hide that while looking like it worked.
        if reason is not None and rating != AssistantMessage.RATING_DOWN:
            return Response(
                {
                    "error": {
                        "code": "invalid_reason",
                        "message": "reason is only valid with rating -1.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # All three of screen, conversation and message are matched in one query, for
        # the reason spelled out in AssistantMessageView: a conversation_id alone was
        # once enough to reach ANY conversation from ANY screen, which also let a white
        # label with the benbot flag off have its rows written through one that had it
        # on. A rating is a smaller write than a message, but it lands on the same rows
        # and would defeat a per-white-label rollback in the same way.
        #
        # `role="assistant"` is part of the lookup rather than a separate 400: a user
        # turn is not a thing this endpoint can rate, so it is simply not found. The
        # matching database constraint is the backstop.
        message = (
            AssistantMessage.objects.filter(
                message_id=message_id,
                conversation_id=conversation_id,
                conversation__screen_uuid=screen.uuid,
                role="assistant",
            )
            .only("message_id", "rating", "rated_at", "rating_reason")
            .first()
        )
        if message is None:
            return Response(
                {"error": {"code": "message_not_found", "message": "No such assistant message."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # `rated_at` is stamped on a clear as well as on a set, and never reset. It is
        # the only thing that distinguishes "rated, then withdrawn" from "never rated"
        # once `rating` is back to NULL, and those are different facts about the reply.
        message.rating = rating
        message.rated_at = timezone.now()
        # Switching to a thumbs-up, or clearing, takes any previous reason with it. A
        # reason stranded on a positive or unrated row would be read as a complaint
        # about a reply nobody complained about — and the DB constraint refuses it
        # anyway, so not doing this would turn an ordinary re-rate into a 500.
        message.rating_reason = reason if rating == AssistantMessage.RATING_DOWN else None
        message.save(update_fields=["rating", "rated_at", "rating_reason"])

        return Response(
            {
                "message_id": str(message.message_id),
                "rating": message.rating,
                "reason": message.rating_reason,
            }
        )
