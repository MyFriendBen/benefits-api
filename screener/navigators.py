"""Which navigators a screen sees on a program's "Get Help Applying" panel.

The results page and Benji show the same navigators, so they select them through the
same functions. `screener.views.update_navigators` serializes what comes back for the
browser (translation dicts the frontend resolves itself); `screener.assistant`
serializes it for the system prompt (flat text, already in the screen's language).
Only the SELECTION lives here, for the same reason `screener.urgent_needs` holds only
the resource selection: the two consumers disagree about shape.

Sharing the selection is the point. Benji is told the navigators it is handed are the
complete set of help-to-apply organizations this household has, and that it may give
their phone numbers — the one thing its guardrails are otherwise strictest about. A
navigator the page shows and Benji doesn't know about makes Benji wrong in a way those
guardrails cannot catch; a navigator Benji offers that the page filtered out for this
county hands someone a number that is not for them. A second implementation of these
four filters would drift, and the drift would surface only mid-conversation.

Four stages, applied per program in this order:

0. `filter_by_white_label` — on a federal program, a navigator applies only when its white
   label is `federal` or in the screen's state (any white label with the same `state_code`,
   so a `cesn` screen sees `co`'s; a white label with no state matches only itself). A federal
   program (`programs.federal`) is one row every white label sees, so it carries every
   state's navigators for that program, and each state should see only its own. County
   scoping can't do this: `filter_by_county` matches on the county name alone, and names
   repeat across states (77 are shared among the WIC states, e.g. Jackson County in CO, KS,
   MO and NC), so a CO navigator listing every CO county would still show in Jackson County,
   MO. Programs on any other white label are not filtered: navigators are global by
   `external_name`, so a state program may use one another white label imported first
   (`lifeline_support_center` is on `wa` and serves MO and KS). A national navigator on a
   federal program belongs on `federal`.
1. `filter_by_county`   — a navigator with counties set applies only in those counties.
   Substring match on the county name, so the screen's "Denver County" matches a County
   row of either "Denver" or "Denver County" (MFB-1602 fixed the data, not this check).
2. `filter_by_required_programs_eligibility` — a navigator with `eligibility_programs`
   applies only when the household is eligible for ALL of them.
3. `referrer_prioritization` — a referrer's `primary_navigators` win when any of them
   survived the first two stages; otherwise the full filtered list stands.
"""

from typing import Optional

from programs.federal import is_federal
from programs.models import Navigator, Program
from screener.models import WhiteLabel


def filter_by_white_label(navigators: list, program: Program, screen_white_label: WhiteLabel) -> list:
    """On a federal program, the navigators owned by `federal` or a white label in the screen's state.

    Reads each navigator's `white_label`, so callers must select it.
    """
    if not is_federal(program):
        return navigators
    return [nav for nav in navigators if _serves_screen(nav.white_label, program, screen_white_label)]


def _serves_screen(navigator_white_label: WhiteLabel, program: Program, screen_white_label: WhiteLabel) -> bool:
    if navigator_white_label.id in (program.white_label_id, screen_white_label.id):
        return True
    state = screen_white_label.state_code
    return bool(state) and navigator_white_label.state_code == state


def filter_by_county(navigators: list, county: Optional[str]) -> list:
    result = []
    for nav in navigators:
        counties = nav.counties.all()
        if len(counties) == 0 or (county is not None and any(county in c.name for c in counties)):
            result.append(nav)
    return result


def filter_by_required_programs_eligibility(navigators: list, program_eligibility: dict) -> list:
    """`program_eligibility` maps name_abbreviated -> anything with an `eligible` attribute.

    The results view passes `Eligibility` objects; the assistant passes
    `ProgramEligibilitySnapshot` rows. Both carry `.eligible`, which is all this reads.
    """
    result = []
    for nav in navigators:
        required = nav.eligibility_programs.all()
        if not required or all(
            getattr(program_eligibility.get(p.name_abbreviated), "eligible", False) for p in required
        ):
            result.append(nav)
    return result


def referrer_prioritization(eligibility_filtered: list, primary_navigators: list) -> list:
    if not primary_navigators:
        return eligibility_filtered
    referrer_navigators = [nav for nav in primary_navigators if nav in eligibility_filtered]
    return referrer_navigators if referrer_navigators else eligibility_filtered


def navigators_for_program(
    program: Program,
    program_eligibility: dict,
    screen_white_label: WhiteLabel,
    screen_county: Optional[str],
    primary_navigators: list,
) -> list[Navigator]:
    """The navigators this household sees on `program`'s page, in the page's order.

    Reads `program.program_navigators` — the ordered through table the admin's
    drag-to-reorder writes — so callers must prefetch `program_navigators__navigator`
    and the navigator's `white_label`, `counties` and `eligibility_programs`, and select
    `program.white_label`, or this is an N+1 per program per filter.
    `primary_navigators` is the referrer's list, already loaded, or empty when the screen
    has no referrer.
    """
    all_navigators = [pn.navigator for pn in program.program_navigators.all()]
    white_label_filtered = filter_by_white_label(all_navigators, program, screen_white_label)
    county_filtered = filter_by_county(white_label_filtered, screen_county)
    eligibility_filtered = filter_by_required_programs_eligibility(county_filtered, program_eligibility)
    return referrer_prioritization(eligibility_filtered, primary_navigators)
