"""
Tests for the screen context Benbot receives (MFB-1427).

`screener.assistant._build_context()` is the only thing standing between the
assistant and a bad recommendation: mfb-ai-service is stateless about our domain
and can only discuss what this payload contains. Two invariants matter.

1. `eligible_programs` must mirror what the results page actually shows the user.
   The frontend hides programs the household already receives and programs worth
   $0 (`filterPrograms.ts:isProgramBasicallyVisible`); if we send them anyway the
   assistant recommends things the user is not looking at.
2. Already-received programs must still reach the assistant, in `current_programs`,
   so it can answer "why did my SNAP stop" instead of pitching a new application.

See the ai-service repo's docs/04-mfb-ai-service-api-contract.md (Layer 2).
"""

import uuid
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import translation
from rest_framework import status
from rest_framework.test import APITestCase

from benefits.tests.cache_override import LOCAL_CACHE
from programs.models import LegalStatus, Program
from screener.assistant import (
    CONTEXT_PREFETCH,
    AssistantMessageRateThrottle,
    AssistantStartRateThrottle,
    AssistantStartView,
    MAX_DOCUMENTS_PER_PROGRAM,
    MAX_PROGRAM_VALUE,
    MAX_PROMPT_TEXT_LEN,
    MAX_VISIBLE_PROGRAMS,
    _build_context,
    _visible_programs,
)
from screener.models import (
    CurrentBenefit,
    EligibilitySnapshot,
    HouseholdMember,
    Insurance,
    ProgramEligibilitySnapshot,
    Screen,
    WhiteLabel,
)
from screener.tests.helpers import seed_document, seed_program, seed_warning
from translations.models import BLANK_TRANSLATION_PLACEHOLDER


def visible(name_abbreviated: str, value=None) -> dict:
    """A `visible_programs` entry as `_visible_programs` normalizes it."""
    return {"name_abbreviated": name_abbreviated, "value": value}


def set_translation(translated_field, text: str) -> None:
    """Set a django-parler translated field's text in the default language.

    seed_program() leaves every translation at BLANK_TRANSLATION_PLACEHOLDER, which
    the context builder treats as "no value" — so tests that care about a real name
    or apply link have to fill it in.

    The language is pinned rather than assumed: `Translation.objects.add_translation`
    writes a row per supported language and leaves parler's active language on the last
    one it touched, so an object handed straight back from a `new_*` manager method
    would otherwise take the text into that language instead of this one.
    """
    translated_field.set_current_language(settings.LANGUAGE_CODE)
    translated_field.text = text
    translated_field.save()


class BuildContextTests(TestCase):
    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="78701",
            household_size=3,
            completed=True,
        )
        seed_program(self.white_label, "snap", "tanf", "wic", "lifeline")
        self.programs = {p.name_abbreviated: p for p in Program.objects.filter(white_label=self.white_label)}

        self.snapshot = EligibilitySnapshot.objects.create(screen=self.screen, is_batch=False, had_error=False)

    def add_snapshot_row(self, name_abbreviated: str, *, value: str = "1200", eligible: bool = True) -> None:
        ProgramEligibilitySnapshot.objects.create(
            eligibility_snapshot=self.snapshot,
            name=name_abbreviated.upper(),
            name_abbreviated=name_abbreviated,
            estimated_value=Decimal(value),
            eligible=eligible,
        )

    def receives(self, *name_abbreviateds: str) -> None:
        for name in name_abbreviateds:
            CurrentBenefit.objects.create(screen=self.screen, program=self.programs[name])
        self.screen.invalidate_current_benefits_cache()

    def context(self, visible=None) -> dict:
        # Reload so the prefetch/cached_property state matches a fresh request
        # rather than whatever setUp left on the instance.
        screen = Screen.objects.prefetch_related(*CONTEXT_PREFETCH).get(pk=self.screen.pk)
        return _build_context(screen, visible)

    def eligible_names(self, context: dict) -> list[str]:
        return [p["external_name"] for p in context["eligible_programs"]]

    def current_names(self, context: dict) -> list[str]:
        return [p["external_name"] for p in context["current_programs"]]

    # --- eligible_programs filtering ---------------------------------------

    def test_eligible_programs_excludes_already_received(self):
        """The MFB-1427 bug: a program the household reported receiving was still
        being offered to the assistant as something to apply for."""
        self.add_snapshot_row("snap")
        self.add_snapshot_row("wic")
        self.receives("snap")

        context = self.context()

        self.assertEqual(self.eligible_names(context), ["wic"])

    def test_eligible_programs_excludes_zero_value(self):
        """The results page hides $0 programs, so the assistant must not see them."""
        self.add_snapshot_row("snap", value="1200")
        self.add_snapshot_row("wic", value="0")

        context = self.context()

        self.assertEqual(self.eligible_names(context), ["snap"])

    def test_eligible_programs_excludes_ineligible(self):
        self.add_snapshot_row("snap")
        self.add_snapshot_row("wic", eligible=False)

        context = self.context()

        self.assertEqual(self.eligible_names(context), ["snap"])

    def test_eligible_programs_sorted_highest_value_first(self):
        self.add_snapshot_row("lifeline", value="111")
        self.add_snapshot_row("snap", value="6636")
        self.add_snapshot_row("wic", value="900")

        context = self.context()

        self.assertEqual(self.eligible_names(context), ["snap", "wic", "lifeline"])

    def test_no_snapshot_yields_empty_eligible_list(self):
        """Allowed by the contract — the assistant is told it has nothing to
        recommend rather than being handed a stale list."""
        EligibilitySnapshot.objects.filter(screen=self.screen).delete()

        context = self.context()

        self.assertEqual(context["eligible_programs"], [])

    def test_apply_url_included_when_link_is_real(self):
        self.add_snapshot_row("snap")
        set_translation(self.programs["snap"].apply_button_link, "https://example.org/apply/snap")

        context = self.context()

        self.assertEqual(context["eligible_programs"][0]["apply_url"], "https://example.org/apply/snap")

    def test_apply_url_omitted_when_link_is_placeholder(self):
        """seed_program leaves the link at BLANK_TRANSLATION_PLACEHOLDER. The key must
        be absent, not empty — the assistant is instructed never to invent a URL."""
        self.add_snapshot_row("snap")

        context = self.context()

        self.assertNotIn("apply_url", context["eligible_programs"][0])

    def test_eligible_program_name_falls_back_when_snapshot_name_is_blank(self):
        """The snapshot's `name` was captured under whatever language was active when
        eligibility ran (unpinned in screener.views), and non-default translation rows
        are created with text="". A blank would render as "- (snap)" in the prompt."""
        ProgramEligibilitySnapshot.objects.create(
            eligibility_snapshot=self.snapshot,
            name="",
            name_abbreviated="snap",
            estimated_value=Decimal("1200"),
            eligible=True,
        )

        context = self.context()

        self.assertEqual(context["eligible_programs"][0]["name"], "snap")

    def test_eligible_program_name_falls_back_on_placeholder(self):
        ProgramEligibilitySnapshot.objects.create(
            eligibility_snapshot=self.snapshot,
            name=BLANK_TRANSLATION_PLACEHOLDER,
            name_abbreviated="snap",
            estimated_value=Decimal("1200"),
            eligible=True,
        )

        context = self.context()

        self.assertEqual(context["eligible_programs"][0]["name"], "snap")

    # --- current_programs ---------------------------------------------------

    def test_current_programs_lists_received_benefits(self):
        self.receives("snap", "tanf")

        context = self.context()

        self.assertEqual(sorted(self.current_names(context)), ["snap", "tanf"])

    def test_current_programs_empty_when_nothing_received(self):
        self.add_snapshot_row("snap")

        context = self.context()

        self.assertEqual(context["current_programs"], [])

    def test_current_programs_includes_benefits_absent_from_snapshot(self):
        """The household told us they receive it, so the assistant should know —
        even when no calculator produced a row for it."""
        self.add_snapshot_row("snap")
        self.receives("tanf")

        context = self.context()

        self.assertEqual(self.current_names(context), ["tanf"])
        self.assertEqual(self.eligible_names(context), ["snap"])

    def test_current_programs_use_translated_name(self):
        set_translation(self.programs["snap"].name, "Basic Food (SNAP)")
        self.receives("snap")

        context = self.context()

        self.assertEqual(context["current_programs"][0]["name"], "Basic Food (SNAP)")

    def test_current_programs_fall_back_to_abbreviation_when_name_blank(self):
        """A missing name translation must not hand the assistant an empty string to
        refer to the program by."""
        self.receives("snap")

        context = self.context()

        self.assertEqual(context["current_programs"][0]["name"], "snap")

    def test_current_programs_carry_no_value_or_apply_url(self):
        """No dollar figure (the estimate is what they *would* get) and no apply link
        (they must never be sent to reapply)."""
        set_translation(self.programs["snap"].apply_button_link, "https://example.org/apply/snap")
        self.receives("snap")

        context = self.context()

        self.assertEqual(set(context["current_programs"][0]), {"external_name", "name"})

    def test_program_is_never_in_both_lists(self):
        """The closed-world rule in the prompt depends on these being disjoint."""
        self.add_snapshot_row("snap")
        self.add_snapshot_row("tanf")
        self.add_snapshot_row("wic")
        self.receives("snap", "tanf")

        context = self.context()

        self.assertEqual(
            set(self.eligible_names(context)) & set(self.current_names(context)),
            set(),
        )

    def test_current_programs_excludes_other_white_labels(self):
        """The prompt describes these lists as a closed universe, so a program from
        another white label must not be able to appear in one."""
        other = WhiteLabel.objects.create(name="Other State", code="other", state_code="OS")
        seed_program(other, "other_snap")
        CurrentBenefit.objects.create(
            screen=self.screen,
            program=Program.objects.get(white_label=other, name_abbreviated="other_snap"),
        )
        self.receives("snap")

        context = self.context()

        self.assertEqual(self.current_names(context), ["snap"])

    def test_current_program_names_do_not_depend_on_request_language(self):
        """Non-default translation rows are created with text="", and because the row
        exists parler's fallback never fires — so reading `.text` under an active
        Spanish locale would hand the assistant empty names. The language must be
        pinned, the way screener.views.default_message does it."""
        set_translation(self.programs["snap"].name, "Basic Food (SNAP)")
        self.receives("snap")

        with translation.override("es"):
            context = self.context()

        self.assertEqual(context["current_programs"][0]["name"], "Basic Food (SNAP)")

    # --- documents ----------------------------------------------------------

    def test_documents_are_included_in_results_page_order(self):
        """The whole point of MFB-1788: asked "what do I need to apply", the assistant
        should read back the same checklist the "more info" panel shows."""
        self.add_snapshot_row("snap")
        for external_name, text in (
            ("proof_of_address", "Proof of address"),
            ("photo_id", "Photo ID"),
            ("proof_of_income", "Proof of income"),
        ):
            seed_document(self.programs["snap"], external_name, text)

        context = self.context()

        self.assertEqual(
            context["eligible_programs"][0]["documents"],
            ["Proof of address", "Photo ID", "Proof of income"],
        )

    def test_documents_key_is_omitted_when_the_program_has_none(self):
        """Absent rather than [] — ai-service defaults it, and the prompt distinguishes
        "we have no list for this program" from "this program needs nothing"."""
        self.add_snapshot_row("snap")

        context = self.context()

        self.assertNotIn("documents", context["eligible_programs"][0])

    def test_blank_and_placeholder_documents_are_dropped(self):
        """`new_document` leaves text="" and the translation machinery writes
        [PLACEHOLDER]; either would render as an empty checklist line."""
        self.add_snapshot_row("snap")
        seed_document(self.programs["snap"], "real", "Proof of address")
        seed_document(self.programs["snap"], "blank", "")
        seed_document(self.programs["snap"], "placeholder", BLANK_TRANSLATION_PLACEHOLDER)

        context = self.context()

        self.assertEqual(context["eligible_programs"][0]["documents"], ["Proof of address"])

    def test_document_urls_never_reach_the_payload(self):
        """Document carries link_url/link_text, and the prompt's LINKS rule is absolute:
        apply links are the only URLs the assistant may share. They are not merely
        unrendered — they are never fetched."""
        self.add_snapshot_row("snap")
        document = seed_document(self.programs["snap"], "proof_of_address", "Proof of address")
        set_translation(document.link_url, "https://example.gov/documents")
        set_translation(document.link_text, "See the document list")

        context = self.context()

        self.assertEqual(context["eligible_programs"][0]["documents"], ["Proof of address"])
        self.assertNotIn("example.gov", str(context))
        self.assertNotIn("See the document list", str(context))

    def test_documents_are_capped_per_program(self):
        """A misconfigured program shouldn't be able to crowd out the rest of the
        prompt."""
        self.add_snapshot_row("snap")
        for i in range(MAX_DOCUMENTS_PER_PROGRAM + 3):
            seed_document(self.programs["snap"], f"doc_{i}", f"Document {i}")

        context = self.context()

        self.assertEqual(len(context["eligible_programs"][0]["documents"]), MAX_DOCUMENTS_PER_PROGRAM)

    def test_document_cap_clears_the_largest_real_program(self):
        """A guard on the constant, not on behavior.

        The cap was originally 12, chosen against the seed configs — where the largest
        documents block is 8. Most of this data is created through the Django admin and
        never reaches a *_initial_config.json, and production (checked 2026-09-10) has
        16 documents on mo_tanf. At 12 the assistant would have handed that household a
        silently short checklist, breaking the results-page parity this feature exists
        for. Lowering the constant below the real maximum must fail a test rather than
        show up as a missing document.
        """
        self.assertGreaterEqual(MAX_DOCUMENTS_PER_PROGRAM, 16)

    def test_over_long_warning_is_clipped_and_reported(self):
        """400 was already clipping production (cccap_jeffco is 562 chars). Clipping an
        instruction mid-sentence is the failure `_apply_url` refuses for links, so if it
        happens at all it must be visible rather than silent."""
        self.add_snapshot_row("snap")
        long_message = "A" * (MAX_PROMPT_TEXT_LEN + 200)
        seed_warning(self.programs["snap"], "_show", long_message)

        with mock.patch("screener.assistant._REPORTED", set()):
            with mock.patch("screener.assistant.capture_message") as reported:
                context = self.context()

        self.assertEqual(len(context["eligible_programs"][0]["warnings"][0]), MAX_PROMPT_TEXT_LEN)
        self.assertEqual(reported.call_count, 1)
        self.assertIn("exceeds MAX_PROMPT_TEXT_LEN", reported.call_args.args[0])

    def test_text_at_the_limit_is_not_reported(self):
        """Resolving at full length is what distinguishes over-long text from text that
        happens to end exactly at the cap; going through _translated's own cap could not
        tell them apart."""
        self.add_snapshot_row("snap")
        seed_warning(self.programs["snap"], "_show", "A" * MAX_PROMPT_TEXT_LEN)

        with mock.patch("screener.assistant._REPORTED", set()):
            with mock.patch("screener.assistant.capture_message") as reported:
                context = self.context()

        self.assertEqual(len(context["eligible_programs"][0]["warnings"][0]), MAX_PROMPT_TEXT_LEN)
        reported.assert_not_called()

    def test_a_static_config_condition_is_reported_once_per_process(self):
        """These conditions are properties of the config, not the request, but they're
        evaluated in a per-program loop on every assistant start. Reporting per request
        would make one unchanging fact the loudest event this module emits."""
        self.add_snapshot_row("snap")
        seed_warning(self.programs["snap"], "not_a_real_calculator", "Should not appear.")

        with mock.patch("screener.assistant._REPORTED", set()):
            with mock.patch("screener.assistant.capture_message") as reported:
                self.context()
                self.context()
                self.context()

        self.assertEqual(reported.call_count, 1)

    def test_documents_are_ordered_deterministically(self):
        """Document declares no Meta.ordering and the M2M is auto-created, so without an
        explicit order_by the sequence is whatever Postgres returns — which need not
        match the results page reading the same rows in a separate query."""
        self.add_snapshot_row("snap")
        first = seed_document(self.programs["snap"], "aaa_last_alphabetically", "Zebra document")
        second = seed_document(self.programs["snap"], "zzz_first_alphabetically", "Apple document")

        documents = self.context()["eligible_programs"][0]["documents"]

        # id order, not insertion-coincidence and not alphabetical by either field.
        self.assertEqual(documents, ["Zebra document", "Apple document"])
        self.assertLess(first.id, second.id)

    def test_documents_use_the_screen_language_not_the_request_language(self):
        """Same reason program names do: `get_language()` reflects the browser's
        Accept-Language, so an English session in a Spanish browser would otherwise get
        a Spanish checklist."""
        self.add_snapshot_row("snap")
        document = seed_document(self.programs["snap"], "proof_of_address", "Proof of address")
        document.text.set_current_language("es")
        document.text.text = "Comprobante de domicilio"
        document.text.save()
        self.screen.request_language_code = "es"
        self.screen.save()

        with translation.override("en-us"):
            context = self.context()

        self.assertEqual(context["eligible_programs"][0]["documents"], ["Comprobante de domicilio"])

    def test_current_programs_carry_documents(self):
        """Recertification needs a document list too ("what do I need to renew my
        SNAP"). Safe on this thinner shape: no dollar value, no apply link."""
        self.receives("snap")
        seed_document(self.programs["snap"], "proof_of_income", "Proof of income")

        context = self.context()

        self.assertEqual(context["current_programs"][0]["documents"], ["Proof of income"])

    # --- warnings -----------------------------------------------------------

    def test_warning_is_included(self):
        self.add_snapshot_row("lifeline")
        seed_warning(
            self.programs["lifeline"],
            "_show",
            "If you are eligible for SNAP, enroll in SNAP before applying for Lifeline.",
        )

        context = self.context()

        self.assertEqual(
            context["eligible_programs"][0]["warnings"],
            ["If you are eligible for SNAP, enroll in SNAP before applying for Lifeline."],
        )

    def test_warnings_key_is_omitted_when_the_program_has_none(self):
        self.add_snapshot_row("snap")

        context = self.context()

        self.assertNotIn("warnings", context["eligible_programs"][0])

    def test_dont_show_warning_is_excluded(self):
        """`_dont_show` is how a warning is switched off in config without deleting it,
        so honouring the calculator matters even for the trivial ones."""
        self.add_snapshot_row("snap")
        seed_warning(self.programs["snap"], "_dont_show", "Should never be shown.")

        context = self.context()

        self.assertNotIn("warnings", context["eligible_programs"][0])

    def test_county_gated_warning_is_included_in_a_matching_county(self):
        self.screen.county = "Denver County"
        self.screen.save()
        self.add_snapshot_row("snap")
        seed_warning(
            self.programs["snap"],
            "_show",
            "Denver applications are processed locally.",
            county_names=("Denver County",),
        )

        context = self.context()

        self.assertEqual(context["eligible_programs"][0]["warnings"], ["Denver applications are processed locally."])

    def test_county_gated_warning_is_excluded_outside_that_county(self):
        """The county gate is the main reason warnings are per-household rather than a
        static field, so bypassing it would show people other counties' instructions."""
        self.screen.county = "Boulder County"
        self.screen.save()
        self.add_snapshot_row("snap")
        seed_warning(
            self.programs["snap"],
            "_show",
            "Denver applications are processed locally.",
            county_names=("Denver County",),
        )

        context = self.context()

        self.assertNotIn("warnings", context["eligible_programs"][0])

    def test_warning_blocked_by_a_missing_dependency_is_excluded(self):
        """`can_calc()` is False when a declared dependency is missing from the screen,
        which is how the results page avoids showing a warning it couldn't evaluate.
        co_snap_student declares `age`; a member with no age puts it in
        `screen.missing_fields()`."""
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=None, student=True)
        self.add_snapshot_row("snap")
        seed_warning(self.programs["snap"], "co_snap_student", "Students face extra SNAP rules.")

        context = self.context()

        self.assertNotIn("warnings", context["eligible_programs"][0])

    def test_warning_with_legal_statuses_is_dropped(self):
        """The results page filters these client-side against the citizenship dropdown,
        which defaults to 'citizen' and is never persisted to the Screen. We can't
        reproduce the selection, so we under-report rather than surface
        immigration-status content to a household that didn't ask for it."""
        self.add_snapshot_row("snap")
        warning = seed_warning(self.programs["snap"], "_show", "Green card holders under 18 are exempt.")
        status_row, _ = LegalStatus.objects.get_or_create(status="gc_under18_no5")
        warning.legal_statuses.add(status_row)

        context = self.context()

        self.assertNotIn("warnings", context["eligible_programs"][0])

    def test_unknown_calculator_is_skipped_rather_than_raising(self):
        """The eligibility run raises on an unrecognized calculator name. Doing that
        here would take the assistant down over a config typo."""
        self.add_snapshot_row("snap")
        seed_warning(self.programs["snap"], "not_a_real_calculator", "Should not appear.")

        context = self.context()

        self.assertNotIn("warnings", context["eligible_programs"][0])
        self.assertEqual(self.eligible_names(context), ["snap"])

    def test_calculator_needing_member_eligibility_is_skipped(self):
        """co_upk reads `eligibility.eligible_members`, which the snapshot has no
        breakdown for. It declares `needs_full_eligibility` so it's skipped
        explicitly instead of silently evaluating against an empty list."""
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=3)
        self.add_snapshot_row("snap")
        seed_warning(self.programs["snap"], "co_upk", "Three-year-olds have a separate application.")

        context = self.context()

        self.assertNotIn("warnings", context["eligible_programs"][0])

    def test_warning_urls_never_reach_the_payload(self):
        """Same rule as documents: WarningMessage carries link_url/link_text and neither
        is fetched."""
        self.add_snapshot_row("snap")
        warning = seed_warning(self.programs["snap"], "_show", "Applications take 6 to 8 months.")
        set_translation(warning.link_url, "https://example.gov/warnings")
        set_translation(warning.link_text, "Read more about delays")

        context = self.context()

        self.assertEqual(context["eligible_programs"][0]["warnings"], ["Applications take 6 to 8 months."])
        self.assertNotIn("example.gov", str(context))
        self.assertNotIn("Read more about delays", str(context))

    def test_warnings_use_the_screen_language_not_the_request_language(self):
        self.add_snapshot_row("snap")
        warning = seed_warning(self.programs["snap"], "_show", "Applications take 6 to 8 months.")
        warning.message.set_current_language("es")
        warning.message.text = "Las solicitudes tardan de 6 a 8 meses."
        warning.message.save()
        self.screen.request_language_code = "es"
        self.screen.save()

        with translation.override("en-us"):
            context = self.context()

        self.assertEqual(context["eligible_programs"][0]["warnings"], ["Las solicitudes tardan de 6 a 8 meses."])

    def test_current_programs_carry_no_warnings(self):
        """Warnings are application caveats for programs the household is being told to
        apply for. This list is the opposite of that."""
        self.receives("snap")
        seed_warning(self.programs["snap"], "_show", "Applications take 6 to 8 months.")

        context = self.context()

        self.assertNotIn("warnings", context["current_programs"][0])

    # --- estimated_delivery_time --------------------------------------------

    def test_estimated_delivery_time_is_forwarded(self):
        """Already on the snapshot and already sent to the results page; answers "how
        long until I actually get this"."""
        ProgramEligibilitySnapshot.objects.create(
            eligibility_snapshot=self.snapshot,
            name="SNAP",
            name_abbreviated="snap",
            estimated_value=Decimal("1200"),
            eligible=True,
            estimated_delivery_time="30 days",
        )

        context = self.context()

        self.assertEqual(context["eligible_programs"][0]["estimated_delivery_time"], "30 days")

    # --- visible_programs intersection --------------------------------------

    def test_visible_programs_narrows_the_eligible_list(self):
        """The client's rendered list is authoritative: several results-page filters
        (legal status, mutual exclusions, per-member insurance) run in the browser and
        can't be reproduced from the snapshot, so anything the page isn't showing must
        not reach the assistant."""
        self.add_snapshot_row("snap")
        self.add_snapshot_row("wic")
        self.add_snapshot_row("lifeline")

        context = self.context(visible=[visible("snap"), visible("lifeline")])

        self.assertEqual(sorted(self.eligible_names(context)), ["lifeline", "snap"])

    def test_visible_programs_cannot_add_programs(self):
        """Untrusted input can only narrow. A name the snapshot doesn't have (or that
        isn't eligible) can't be smuggled in."""
        self.add_snapshot_row("snap")
        self.add_snapshot_row("wic", eligible=False)

        context = self.context(visible=[visible("snap"), visible("wic"), visible("not_a_program")])

        self.assertEqual(self.eligible_names(context), ["snap"])

    def test_visible_programs_still_excludes_already_received(self):
        """Belt and braces: the server-side gates stay on even when the client sends a
        list, so a frontend bug can't reintroduce the MFB-1427 behavior."""
        self.add_snapshot_row("snap")
        self.receives("snap")

        context = self.context(visible=[visible("snap")])

        self.assertEqual(self.eligible_names(context), [])
        self.assertEqual(self.current_names(context), ["snap"])

    def test_empty_visible_list_is_respected(self):
        """An empty results page is a real state, and it's the one where the assistant
        must not recommend anything — so it has to be distinguishable from "not sent"."""
        self.add_snapshot_row("snap")

        context = self.context(visible=[])

        self.assertEqual(context["eligible_programs"], [])

    # --- displayed values ---------------------------------------------------

    def test_client_value_overrides_the_snapshot_value(self):
        """The results page reduces a program's value per member who already holds its
        insurance; the snapshot sums all members. The assistant must quote the figure
        the user can actually see."""
        self.add_snapshot_row("snap", value="9000")

        context = self.context(visible=[visible("snap", 3000)])

        self.assertEqual(context["eligible_programs"][0]["estimated_value"], 3000)

    def test_snapshot_value_used_when_client_sends_no_value(self):
        """Older frontend builds send bare name strings."""
        self.add_snapshot_row("snap", value="9000")

        context = self.context(visible=[visible("snap")])

        self.assertEqual(context["eligible_programs"][0]["estimated_value"], 9000)

    def test_sort_order_follows_the_displayed_values(self):
        """ "Your biggest one" has to agree with what's on their screen."""
        self.add_snapshot_row("snap", value="9000")
        self.add_snapshot_row("wic", value="1000")

        context = self.context(visible=[visible("snap", 500), visible("wic", 1000)])

        self.assertEqual(self.eligible_names(context), ["wic", "snap"])

    def test_client_value_cannot_exceed_the_snapshot(self):
        """The results page can only ever *reduce* the snapshot value (per covered
        member), so anything above it is definitionally not a displayed value.

        The bound is load-bearing, not cosmetic: AssistantStartView is AllowAny and the
        screen UUID is also the results-page URL, and ai-service resumes by screen_uuid
        and overwrites the stored context — so without this, anyone who has seen a link
        could make that household's assistant quote an arbitrary amount."""
        self.add_snapshot_row("snap", value="6636")

        context = self.context(visible=[visible("snap", 999_999)])

        self.assertEqual(context["eligible_programs"][0]["estimated_value"], 6636)

    def test_client_value_of_zero_is_treated_as_hidden(self):
        """The $0 gate must test the DISPLAYED figure, or a client value of 0 slips a
        "~$0 per year" program in — exactly the row the results page hides."""
        self.add_snapshot_row("snap", value="1200")
        self.add_snapshot_row("wic", value="1200")

        context = self.context(visible=[visible("snap", 0), visible("wic", 900)])

        self.assertEqual(self.eligible_names(context), ["wic"])

    def test_visible_programs_matching_nothing_falls_back(self):
        """A list that matches no eligible row is malformed input, not an empty results
        page. Without the fallback, `visible_programs: ["zzz"]` empties the list and
        ai-service renders (and persists) "this person has NO eligible programs"."""
        self.add_snapshot_row("snap")
        self.add_snapshot_row("wic")

        context = self.context(visible=[visible("zzz")])

        self.assertEqual(sorted(self.eligible_names(context)), ["snap", "wic"])

    def test_empty_visible_list_is_still_respected_after_the_fallback(self):
        """An explicit [] means "showing nothing" and must stay distinguishable from
        "names matched nothing"."""
        self.add_snapshot_row("snap")

        context = self.context(visible=[])

        self.assertEqual(context["eligible_programs"], [])

    def test_duplicate_visible_names_take_the_first_value(self):
        """Last-wins would let a caller send the same program twice to choose which
        value applies."""
        self.add_snapshot_row("snap", value="6636")

        parsed = _visible_programs(
            {
                "visible_programs": [
                    {"name_abbreviated": "snap", "value": 100},
                    {"name_abbreviated": "snap", "value": 5000},
                ]
            }
        )
        context = self.context(visible=parsed)

        self.assertEqual(context["eligible_programs"][0]["estimated_value"], 100)

    # --- member-level insurance ---------------------------------------------

    def test_member_insurance_excludes_the_program(self):
        """Medicaid/CHP enrollment lives in Insurance.insurance_map(), not
        CurrentBenefit — so has_benefit() can't see it and a household already on
        Medicaid was getting Medicaid recommended."""
        seed_program(self.white_label, "medicaid")
        self.programs = {p.name_abbreviated: p for p in Program.objects.filter(white_label=self.white_label)}
        self.add_snapshot_row("medicaid")
        self.add_snapshot_row("snap")

        member = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        Insurance.objects.create(household_member=member, medicaid=True)

        context = self.context()

        self.assertEqual(self.eligible_names(context), ["snap"])

    def test_member_insurance_gate_does_not_override_a_client_list(self):
        """The client list is authoritative *precisely because* per-member insurance runs
        client-side. `_has_member_insurance` is coarser than the page — it hides where
        the page reduces the value — so applying it on top would drop a program the user
        is looking at: the MFB-1427 failure in reverse."""
        seed_program(self.white_label, "medicaid")
        self.programs = {p.name_abbreviated: p for p in Program.objects.filter(white_label=self.white_label)}
        self.add_snapshot_row("medicaid")
        member = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        Insurance.objects.create(household_member=member, medicaid=True)

        context = self.context(visible=[visible("medicaid", 5280)])

        self.assertEqual(self.eligible_names(context), ["medicaid"])

    def test_insurance_held_program_appears_in_current_programs(self):
        """Medicaid/CHP enrollment lives only in Insurance, so without the union it was
        removed from eligible AND absent from current — and the closed-world rule then
        forbids the assistant from naming it at all."""
        seed_program(self.white_label, "medicaid")
        member = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        Insurance.objects.create(household_member=member, medicaid=True)

        context = self.context()

        self.assertIn("medicaid", self.current_names(context))

    def test_member_insurance_check_ignores_unmapped_programs(self):
        """strict=False means a program absent from insurance_map returns False, so this
        gate is safe to run for every program."""
        self.add_snapshot_row("snap")
        member = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        Insurance.objects.create(household_member=member, medicaid=True)

        context = self.context()

        self.assertEqual(self.eligible_names(context), ["snap"])

    def test_omitted_visible_list_falls_back_to_server_filters(self):
        """Older frontend builds and non-web channels send nothing; they must still get
        a sensibly filtered list rather than an empty one."""
        self.add_snapshot_row("snap")
        self.add_snapshot_row("wic")

        context = self.context()

        self.assertEqual(sorted(self.eligible_names(context)), ["snap", "wic"])

    # --- review-round findings ----------------------------------------------

    def test_a_long_apply_url_is_not_truncated(self):
        """Two links in the shipped seed config exceed MAX_PROMPT_FIELD_LEN (tx_wic at
        198 chars, il_ibccp at 174). Truncating a URL produces an authoritative-looking
        404, and the prompt forbids the assistant from offering any other link — so
        there'd be no fallback. URLs are validated, not clipped."""
        long_url = "https://mywic.us/participantreferral?program=TX&_gl=1*" + ("a" * 140)
        self.assertGreater(len(long_url), 160)
        self.add_snapshot_row("snap")
        set_translation(self.programs["snap"].apply_button_link, long_url)

        context = self.context()

        self.assertEqual(context["eligible_programs"][0]["apply_url"], long_url)

    def test_an_absurdly_long_apply_url_is_dropped_not_truncated(self):
        self.add_snapshot_row("snap")
        set_translation(self.programs["snap"].apply_button_link, "https://x.example/?q=" + ("a" * 600))

        context = self.context()

        self.assertNotIn("apply_url", context["eligible_programs"][0])

    def test_insurance_is_detected_via_base_program(self):
        """`insurance_map()` has a generic `medicaid` key but no `ks_medicaid`, and
        several state variants aren't listed at all. Resolving through `base_program` —
        the same structural grouping `has_base_benefit` reads — covers them without a
        hand-maintained list."""
        Program.objects.new_program(self.white_label.code, "ks_medicaid")
        Program.objects.filter(name_abbreviated="ks_medicaid").update(base_program="medicaid")
        self.add_snapshot_row("ks_medicaid")
        self.add_snapshot_row("snap")
        member = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        Insurance.objects.create(household_member=member, medicaid=True)

        context = self.context()

        self.assertEqual(self.eligible_names(context), ["snap"])
        self.assertIn("ks_medicaid", self.current_names(context))

    def test_lists_stay_disjoint_when_a_client_list_is_supplied(self):
        """The insurance gate is skipped for a client list (it's coarser than the page),
        but the insurance union in current_programs is unconditional — so a
        partially-enrolled household could otherwise land the same program in both
        lists, telling the assistant "recommend it, apply here" and "they already have
        it" in one payload."""
        Program.objects.new_program(self.white_label.code, "co_medicaid")
        self.add_snapshot_row("co_medicaid")
        member = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        Insurance.objects.create(household_member=member, medicaid=True)

        context = self.context(visible=[visible("co_medicaid", 5280)])

        self.assertEqual(self.eligible_names(context), ["co_medicaid"])
        self.assertNotIn("co_medicaid", self.current_names(context))
        self.assertEqual(set(self.eligible_names(context)) & set(self.current_names(context)), set())

    def test_a_valid_client_list_is_not_discarded_when_the_gates_empty_it(self):
        """The page is showing only SNAP; the household then toggles "I already receive
        SNAP" in another tab. `has_benefit` empties the list — but the client list was
        never malformed, so falling back would hand over programs the page hid for legal
        status and excludes_programs. Test the intersection, not the outcome."""
        self.add_snapshot_row("snap")
        self.add_snapshot_row("wic")  # hidden client-side, must not reappear
        self.receives("snap")

        context = self.context(visible=[visible("snap")])

        self.assertEqual(context["eligible_programs"], [])
        self.assertEqual(self.current_names(context), ["snap"])

    def test_translation_falls_back_when_the_requested_language_has_no_row(self):
        """`TranslationDoesNotExist` subclasses AttributeError, so returning on it
        skipped the LANGUAGE_CODE fallback entirely — degrading every name to its
        abbreviation for the whole conversation."""
        set_translation(self.programs["snap"].name, "Basic Food (SNAP)")
        self.receives("snap")
        self.screen.request_language_code = "ar"  # no row for this language
        self.screen.save()

        context = self.context()

        self.assertEqual(context["current_programs"][0]["name"], "Basic Food (SNAP)")

    # --- results_url --------------------------------------------------------

    def test_results_url_is_included(self):
        """The assistant's guardrails offer "your results page" as the fallback when it
        has nothing it may recommend. That fallback was dead — the key was never sent."""
        context = self.context()

        self.assertEqual(
            context["results_url"],
            f"{settings.FRONTEND_DOMAIN}/{self.white_label.code}/{self.screen.uuid}/results/benefits",
        )

    # --- household ----------------------------------------------------------

    def test_household_size_included(self):
        context = self.context()

        self.assertEqual(context["household"], {"size": 3})

    # --- query count --------------------------------------------------------
    #
    # (see also VisibleProgramsParsingTests below, which needs no database)

    def test_context_build_does_not_scale_queries_with_program_count(self):
        """_build_context runs on every assistant open, and resolving a translated
        program name is the easy place to regress into an N+1: Program.name is an FK to
        Translation, but Translation is a parler model whose text lives in a separate
        table, so `select_related("name")` alone still resolves `.text` per row.

        Asserts flatness rather than a fixed count — the absolute number depends on
        unrelated lookups, but it must not grow with the number of programs.
        """

        def query_count() -> int:
            # Reload so prefetch/cached_property state matches a fresh request.
            screen = Screen.objects.prefetch_related(*CONTEXT_PREFETCH).get(pk=self.screen.pk)
            with CaptureQueriesContext(connection) as captured:
                _build_context(screen)
            return len(captured)

        self.add_snapshot_row("snap")
        self.receives("tanf")
        set_translation(self.programs["tanf"].name, "TANF")
        # Documents and warnings hang off Program the same way, and are resolved
        # per program — so they belong on both sides of this comparison, or the
        # constant-query claim only covers the fields that existed before MFB-1788.
        seed_document(self.programs["snap"], "snap_id", "Photo ID")
        seed_document(self.programs["tanf"], "tanf_id", "Photo ID")
        # _tax_unit, not just _show: _show reads nothing, so it cannot exercise the
        # axis that scales. _tax_unit reaches Screen.has_members_outside_of_tax_unit ->
        # is_dependent -> get_reference_date, which is unprefetchable by construction
        # (order_by builds a fresh queryset) and was an N+1 on members x programs until
        # that method was memoized.
        seed_warning(self.programs["snap"], "_tax_unit", "SNAP has tax-unit rules.")
        seed_warning(self.programs["tanf"], "_show", "TANF applications take a while.")
        with_one = query_count()

        self.add_snapshot_row("wic")
        self.receives("lifeline")
        set_translation(self.programs["lifeline"].name, "Lifeline")
        seed_document(self.programs["wic"], "wic_id", "Photo ID")
        seed_document(self.programs["lifeline"], "lifeline_id", "Photo ID")
        seed_warning(self.programs["wic"], "_tax_unit", "WIC has tax-unit rules.")
        seed_warning(self.programs["lifeline"], "_show", "Lifeline takes a while.")
        with_two = query_count()

        self.assertEqual(with_one, with_two)

    def test_context_build_does_not_scale_queries_with_member_count(self):
        """The insurance check walks household_members (and each member's reverse
        OneToOne `insurance`) once per program, so it's an N+1 on two axes at once
        unless household_members__insurance is prefetched. Warning evaluation walks
        them again through screen.missing_fields()."""

        def query_count() -> int:
            screen = Screen.objects.prefetch_related(*CONTEXT_PREFETCH).get(pk=self.screen.pk)
            with CaptureQueriesContext(connection) as captured:
                _build_context(screen)
            return len(captured)

        self.add_snapshot_row("snap")
        self.add_snapshot_row("wic")
        # Evaluating a warning calls screen.missing_fields(), which walks every member
        # plus each member's reverse `insurance`/`energy_calculator` and their income
        # streams — a third N+1 axis unless CONTEXT_PREFETCH covers them.
        # _tax_unit walks every member (see the sibling test); _show would keep this
        # flat no matter how badly the member axis regressed.
        seed_warning(self.programs["snap"], "_tax_unit", "SNAP has tax-unit rules.")
        seed_warning(self.programs["wic"], "_show", "WIC applications take a while.")

        # The baseline needs a member who is neither head nor spouse. `is_in_tax_unit`
        # short-circuits on those two, so a head-only household never reaches
        # `is_dependent` and never reads the reference date — measuring from there would
        # compare a run that skips a branch against one that takes it, and report the
        # branch as growth.
        for relationship, age in (("headOfHousehold", 40), ("child", 10)):
            member = HouseholdMember.objects.create(screen=self.screen, relationship=relationship, age=age)
            Insurance.objects.create(household_member=member, employer=True)
        with_two_members = query_count()

        for age in (38, 12, 14):
            extra = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=age)
            Insurance.objects.create(household_member=extra, employer=True)
        with_five_members = query_count()

        self.assertEqual(with_two_members, with_five_members)


class VisibleProgramsParsingTests(SimpleTestCase):
    """`visible_programs` is untrusted browser input. It can only ever narrow the
    program list (it's intersected with the snapshot), so the risk isn't injection —
    it's a malformed value silently blanking the assistant's list, or an unbounded
    one. No database needed."""

    def parse(self, value, present=True):
        # Takes a plain dict now rather than a request, so there's no fake request
        # object to keep in sync with DRF.
        return _visible_programs({"visible_programs": value} if present else {})

    def test_absent_key_returns_none(self):
        """None selects the server-side fallback filters."""
        self.assertIsNone(self.parse(None, present=False))

    def test_bare_string_list_is_normalized(self):
        """The older frontend shape — names only, no values."""
        self.assertEqual(
            self.parse([" SNAP ", "Wic"]),
            [visible("snap"), visible("wic")],
        )

    def test_object_list_carries_values(self):
        self.assertEqual(
            self.parse([{"name_abbreviated": "SNAP", "value": 6636}]),
            [visible("snap", 6636)],
        )

    def test_mixed_shapes_are_accepted(self):
        self.assertEqual(
            self.parse(["snap", {"name_abbreviated": "wic", "value": 1224}]),
            [visible("snap"), visible("wic", 1224)],
        )

    def test_empty_list_is_preserved(self):
        """Distinct from absent: the results page really is rendering nothing, and the
        assistant must be told it has nothing to recommend."""
        self.assertEqual(self.parse([]), [])

    def test_non_list_returns_none(self):
        for value in ("snap", 42, {"snap": True}):
            with self.subTest(value=value):
                self.assertIsNone(self.parse(value))

    def test_unusable_entries_are_dropped(self):
        self.assertEqual(
            self.parse(["snap", None, 7, {"value": 100}, {"name_abbreviated": ""}, "wic"]),
            [visible("snap"), visible("wic")],
        )

    def test_all_junk_entries_fall_back_rather_than_blanking(self):
        """A list that had content but normalized to nothing is malformed input, not a
        genuine empty page — returning [] there would silence the assistant."""
        self.assertIsNone(self.parse([None, "", "   "]))

    def test_oversized_list_is_truncated(self):
        self.assertEqual(
            len(self.parse([f"program_{i}" for i in range(MAX_VISIBLE_PROGRAMS + 50)])), MAX_VISIBLE_PROGRAMS
        )

    # `value` is the one field taken on trust, since being what the user sees is the
    # whole point of it — so a bad one must degrade to the snapshot, never be quoted.
    def test_bad_values_fall_back_to_the_snapshot(self):
        for bad in (-1, MAX_PROGRAM_VALUE + 1, True, False, "6636", None, float("nan"), float("inf")):
            with self.subTest(value=bad):
                parsed = self.parse([{"name_abbreviated": "snap", "value": bad}])
                self.assertEqual(parsed, [visible("snap")], f"{bad!r} should have been rejected")

    def test_zero_is_a_valid_value(self):
        self.assertEqual(self.parse([{"name_abbreviated": "snap", "value": 0}]), [visible("snap", 0)])

    def test_float_values_are_truncated_to_whole_dollars(self):
        self.assertEqual(self.parse([{"name_abbreviated": "snap", "value": 6636.7}]), [visible("snap", 6636)])


class AssistantStartViewTests(APITestCase):
    """End-to-end through the view.

    Without this, both halves of the feature are tested and the join between them is
    not: deleting `_visible_programs(body)` from the view, or deleting CONTEXT_PREFETCH
    from its queryset, left the whole unit suite green (the N+1 tests supply the
    prefetch themselves, which makes them tautological with respect to the constant).
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(
            name="Test State", code="test", state_code="TS", feature_flags={"benbot": True}
        )
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", household_size=2, completed=True
        )
        seed_program(self.white_label, "snap", "wic")
        snapshot = EligibilitySnapshot.objects.create(screen=self.screen, is_batch=False, had_error=False)
        for name, value in (("snap", "6636"), ("wic", "1224")):
            ProgramEligibilitySnapshot.objects.create(
                eligibility_snapshot=snapshot,
                name=name.upper(),
                name_abbreviated=name,
                estimated_value=Decimal(value),
                eligible=True,
            )
        # Documents and warnings are populated so the query bound below covers the
        # prefetches they need. Django skips a nested prefetch whose parent set is
        # empty, so a fixture without them silently exempts the whole chain from the
        # ceiling — which is exactly the coverage this class exists to provide.
        snap, wic = (Program.objects.get(white_label=self.white_label, name_abbreviated=n) for n in ("snap", "wic"))
        for program in (snap, wic):
            seed_document(program, f"{program.name_abbreviated}_id", "Photo ID")
            seed_warning(program, "_show", f"{program.name_abbreviated} applications take a while.")
        self.url = reverse("assistant-start", args=[self.screen.uuid])

    def _post(self, body):
        """POST and return the payload the view forwarded to ai-service."""
        with mock.patch("screener.assistant.requests.request") as request:
            request.return_value = mock.Mock(status_code=201, json=lambda: {"conversation_id": "c1", "messages": []})
            response = self.client.post(self.url, body, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return request.call_args.kwargs["json"]

    def test_visible_programs_from_the_request_reaches_the_context(self):
        payload = self._post({"visible_programs": [{"name_abbreviated": "wic", "value": 900}]})

        eligible = payload["context"]["eligible_programs"]
        self.assertEqual([p["external_name"] for p in eligible], ["wic"])
        self.assertEqual(eligible[0]["estimated_value"], 900)

    def test_omitting_visible_programs_uses_the_server_filters(self):
        payload = self._post({})

        eligible = payload["context"]["eligible_programs"]
        self.assertEqual(sorted(p["external_name"] for p in eligible), ["snap", "wic"])

    def test_json_array_body_does_not_500(self):
        """`request.data` is a list for an array body, so `.get` isn't safe to assume."""
        with mock.patch("screener.assistant.requests.request") as request:
            request.return_value = mock.Mock(status_code=201, json=lambda: {})
            response = self.client.post(self.url, [], format="json")

        self.assertEqual(response.status_code, 201)

    # Ceiling rather than an exact count: an exact number makes an unambiguous
    # improvement (adding a select_related) look like a regression, which is what
    # happened when `white_label` was added to the view's queryset.
    #
    # Raised from 10 for MFB-1788: the four CONTEXT_PREFETCH entries that feed
    # screen.missing_fields(), plus documents and warnings (each with their counties,
    # legal statuses and translations) on the one Program fetch _build_context already
    # made. All flat in program and member count — the sibling tests assert that.
    MAX_START_QUERIES = 16

    def test_query_count_is_bounded(self):
        """Bounded here so CONTEXT_PREFETCH disappearing from the view is caught, even
        though the unit-level N+1 tests supply the prefetch themselves and so can't see
        the constant going missing.

        Roughly: screen (+white_label joined), the CONTEXT_PREFETCH prefetches,
        snapshot, its program_snapshots prefetch, the insurance name/base_program lookup,
        the apply-link programs + their translations prefetch, and current_programs. All
        flat in program and member count — which is what the sibling tests assert.
        """
        with mock.patch("screener.assistant.requests.request") as request:
            request.return_value = mock.Mock(status_code=201, json=lambda: {})
            with CaptureQueriesContext(connection) as captured:
                self.client.post(self.url, {}, format="json")

        self.assertLessEqual(len(captured), self.MAX_START_QUERIES, f"{len(captured)} queries")

    def test_feature_flag_off_returns_403(self):
        self.white_label.feature_flags = {"benbot": False}
        self.white_label.save()

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 403)


@override_settings(CACHES=LOCAL_CACHE)
class AssistantThrottleTests(APITestCase):
    """The throttles are on AllowAny endpoints that proxy to a paid LLM, so "it's
    configured" isn't enough — assert one actually engages and returns 429.

    Throttle history is cache-backed, so these tests pin the cache to a per-process
    LocMemCache. Left on the ambient backend they share one Redis with every other
    test process, and a concurrent run spending part of the 30/hour budget makes the
    429 assertion fail for reasons unrelated to throttling. The clears below keep the
    budget clean between tests within this process.
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.white_label = WhiteLabel.objects.create(
            name="Test State", code="test", state_code="TS", feature_flags={"benbot": True}
        )
        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", household_size=1, completed=True
        )
        self.url = reverse("assistant-start", args=[self.screen.uuid])

    def test_start_endpoint_throttles_and_returns_429(self):
        rate = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["assistant_start"]
        limit = int(rate.split("/")[0])

        with mock.patch("screener.assistant.requests.request") as request:
            request.return_value = mock.Mock(status_code=201, json=lambda: {})
            statuses = [self.client.post(self.url, {}, format="json").status_code for _ in range(limit + 1)]

        self.assertEqual(statuses[-1], status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertNotIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses[:limit])

    def test_message_endpoint_has_its_own_scope(self):
        """Separate scopes so a long conversation can't exhaust the open budget."""
        self.assertEqual(AssistantStartRateThrottle.scope, "assistant_start")
        self.assertEqual(AssistantMessageRateThrottle.scope, "assistant_message")
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        self.assertIn("assistant_start", rates)
        self.assertIn("assistant_message", rates)


class AssistantHistoryViewTests(APITestCase):
    """GET on the conversations path — read a transcript back, creating nothing.

    Exists so the chat widget can restore a returning household's conversation when it
    opens. The emailed results link returns them to the same `screen_uuid`, so their
    history is on the other end of this call; before it, the widget showed the generic
    welcome and their transcript only appeared once they sent another message.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(
            name="Test State", code="test", state_code="TS", feature_flags={"benbot": True}
        )
        self.screen = Screen.objects.create(white_label=self.white_label, completed=True, household_size=2)
        self.url = reverse("assistant-start", args=[self.screen.uuid])

    def _get(self, upstream_status=200, upstream_body=None):
        with mock.patch("screener.assistant.requests.request") as request:
            request.return_value = mock.Mock(
                status_code=upstream_status,
                json=lambda: upstream_body if upstream_body is not None else {"conversation_id": "c1", "messages": []},
            )
            response = self.client.get(self.url)
        return response, request

    def test_forwards_the_screen_uuid_as_a_query_parameter(self):
        response, request = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.call_args.args[0], "GET")
        self.assertTrue(request.call_args.args[1].endswith("/v1/conversations"))
        self.assertEqual(request.call_args.kwargs["params"], {"screen_uuid": str(self.screen.uuid)})

    def test_sends_no_request_body(self):
        """A GET carrying a JSON body is not handled predictably by every intermediary,
        and ai-service reads the screen id from the query string."""
        _, request = self._get()

        self.assertIsNone(request.call_args.kwargs["json"])

    def test_passes_the_transcript_through(self):
        body = {
            "conversation_id": "c1",
            "messages": [
                {"message_id": "m1", "role": "user", "text": "what about WIC?", "created_at": "2026-09-01T00:00:00Z"},
                {"message_id": "m2", "role": "assistant", "text": "here you go", "created_at": "2026-09-01T00:00:01Z"},
            ],
        }
        response, _ = self._get(upstream_body=body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([m["text"] for m in response.data["messages"]], ["what about WIC?", "here you go"])

    def test_no_history_passes_the_404_through(self):
        """The common case for a first-time visitor, and not an error — the frontend
        reads it as "nothing to restore"."""
        response, _ = self._get(
            upstream_status=404,
            upstream_body={"error": {"code": "conversation_not_found", "message": "none"}},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "conversation_not_found")

    def test_assembles_no_context(self):
        """A read must not build or send context. The POST refreshes ai-service's
        stored snapshot; if this did too, merely opening the widget would overwrite the
        context an in-flight conversation is reasoning from (the MFB-1427 failure)."""
        _, request = self._get()

        self.assertNotIn("context", request.call_args.kwargs.get("params") or {})
        self.assertIsNone(request.call_args.kwargs["json"])

    def test_disabled_flag_is_403_and_calls_nothing(self):
        self.white_label.feature_flags = {"benbot": False}
        self.white_label.save()

        with mock.patch("screener.assistant.requests.request") as request:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
        request.assert_not_called()

    def test_unknown_screen_is_404_and_calls_nothing(self):
        url = reverse("assistant-start", args=[uuid.uuid4()])

        with mock.patch("screener.assistant.requests.request") as request:
            response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        request.assert_not_called()

    def test_read_uses_its_own_throttle_not_the_start_budget(self):
        """Reads are cheap and frequent (the widget opens on nearly every results page,
        and a reload repeats it). On the 30/hour start budget, ordinary browsing would
        exhaust a household's ability to open a conversation at all.
        """
        view = AssistantStartView()
        view.request = mock.Mock(method="GET")

        throttles = view.get_throttles()

        self.assertEqual([t.scope for t in throttles], ["assistant_history"])

    def test_post_still_uses_the_start_throttle(self):
        view = AssistantStartView()
        view.request = mock.Mock(method="POST")

        throttles = view.get_throttles()

        self.assertEqual([t.scope for t in throttles], ["assistant_start"])

    def test_head_is_throttled_as_a_read_not_as_a_start(self):
        """Django's `View.setup` aliases HEAD to the `get` handler when no `head` is
        defined, so a HEAD request is served by the read path and must be charged to
        the read budget. Matching only "GET" put it on the 30/hour start budget — the
        exact inversion `get_throttles` exists to prevent, and the throttle keys on
        client IP, so one scanner or prefetcher would spend that budget for everyone
        behind the same address.
        """
        view = AssistantStartView()
        view.request = mock.Mock(method="HEAD")

        throttles = view.get_throttles()

        self.assertEqual([t.scope for t in throttles], ["assistant_history"])

    def test_head_reaches_the_read_handler(self):
        """Pins the aliasing the test above depends on, so it cannot quietly stop being
        true (by someone defining a `head` method, say) and leave that test vacuous."""
        with mock.patch("screener.assistant.requests.request") as request:
            request.return_value = mock.Mock(status_code=200, json=lambda: {"conversation_id": "c1", "messages": []})
            response = self.client.head(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.call_args.args[0], "GET")
