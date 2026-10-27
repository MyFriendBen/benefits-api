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
three filters would drift, and the drift would surface only mid-conversation.

Three stages, applied per program in this order (MFB-666):

1. `filter_by_county`   — a navigator with counties set applies only in those counties.
   Substring match on the county name, so the screen's "Denver County" matches a County
   row of either "Denver" or "Denver County" (MFB-1602 fixed the data, not this check).
2. `filter_by_required_programs_eligibility` — a navigator with `eligibility_programs`
   applies only when the household is eligible for ALL of them.
3. `referrer_prioritization` — a referrer's `primary_navigators` win when any of them
   survived the first two stages; otherwise the full filtered list stands.
"""

from typing import Optional

from programs.models import Navigator, Program


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
    screen_county: Optional[str],
    primary_navigators: list,
) -> list[Navigator]:
    """The navigators this household sees on `program`'s page, in the page's order.

    Reads `program.program_navigators` — the ordered through table the admin's
    drag-to-reorder writes — so callers must prefetch `program_navigators__navigator`
    and the navigator's `counties` and `eligibility_programs`, or this is an N+1 per
    program per filter. `primary_navigators` is the referrer's list, already loaded, or
    empty when the screen has no referrer.
    """
    all_navigators = [pn.navigator for pn in program.program_navigators.all()]
    county_filtered = filter_by_county(all_navigators, screen_county)
    eligibility_filtered = filter_by_required_programs_eligibility(county_filtered, program_eligibility)
    return referrer_prioritization(eligibility_filtered, primary_navigators)
