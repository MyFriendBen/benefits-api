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

from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import translation
from rest_framework import status
from rest_framework.test import APITestCase

from programs.models import Program
from screener.assistant import (
    CONTEXT_PREFETCH,
    AssistantMessageRateThrottle,
    AssistantStartRateThrottle,
    MAX_PROGRAM_VALUE,
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
from screener.tests.helpers import seed_program
from translations.models import BLANK_TRANSLATION_PLACEHOLDER


def visible(name_abbreviated: str, value=None) -> dict:
    """A `visible_programs` entry as `_visible_programs` normalizes it."""
    return {"name_abbreviated": name_abbreviated, "value": value}


def set_translation(translated_field, text: str) -> None:
    """Set a django-parler translated field's text in the default language.

    seed_program() leaves every translation at BLANK_TRANSLATION_PLACEHOLDER, which
    the context builder treats as "no value" — so tests that care about a real name
    or apply link have to fill it in.
    """
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
        with_one = query_count()

        self.add_snapshot_row("wic")
        self.receives("lifeline")
        set_translation(self.programs["lifeline"].name, "Lifeline")
        with_two = query_count()

        self.assertEqual(with_one, with_two)

    def test_context_build_does_not_scale_queries_with_member_count(self):
        """The insurance check walks household_members (and each member's reverse
        OneToOne `insurance`) once per program, so it's an N+1 on two axes at once
        unless household_members__insurance is prefetched."""

        def query_count() -> int:
            screen = Screen.objects.prefetch_related(*CONTEXT_PREFETCH).get(pk=self.screen.pk)
            with CaptureQueriesContext(connection) as captured:
                _build_context(screen)
            return len(captured)

        self.add_snapshot_row("snap")
        self.add_snapshot_row("wic")
        member = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=40)
        Insurance.objects.create(household_member=member, employer=True)
        with_one_member = query_count()

        for age in (38, 10, 12):
            extra = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=age)
            Insurance.objects.create(household_member=extra, employer=True)
        with_four_members = query_count()

        self.assertEqual(with_one_member, with_four_members)


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
    MAX_START_QUERIES = 10

    def test_query_count_is_bounded(self):
        """Bounded here so CONTEXT_PREFETCH disappearing from the view is caught, even
        though the unit-level N+1 tests supply the prefetch themselves and so can't see
        the constant going missing.

        Roughly: screen (+white_label joined), the two CONTEXT_PREFETCH prefetches,
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


class AssistantThrottleTests(APITestCase):
    """The throttles are on AllowAny endpoints that proxy to a paid LLM, so "it's
    configured" isn't enough — assert one actually engages and returns 429.

    Throttle history is cache-backed and LocMemCache is shared for the whole test
    session, so every test here clears it. Without that, `AssistantStartViewTests`
    spending part of the 30/hour budget would eventually make these fail for unrelated
    reasons — and vice versa.
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
