"""
Federal programs: one `Program` row under the `federal` white label, shown to every white
label instead of a copy per state.

A federal row is prefixed like every other white label's — `federal_trump_account`, not
`trump_account` — so no program is left under a bare name. The prefix is also the
calculator's `program_code`, because the registry resolves a calculator by matching it to
`Program.name_abbreviated`.

That prefix means a federal row never shares a name with the state rows it replaces, so no
name comparison can tell the two apart. There is therefore no name-based duplicate check:
one would read as protection while being unable to fire. Each program's move still
deactivates its state rows, and the move's own ticket lists every row it switches off,
checked against prod — that list is what makes a move safe.

The helpers below match on the white label, not the name, and so are unaffected by the
prefix. `preferred_program` and `filter_programs_by_name` resolve a name that matches two
rows; with prefixed names they no longer find a collision to resolve, and are kept for the
un-prefixed rows that predate this and for callers that key results by name.
"""

import logging
from typing import TYPE_CHECKING, Iterable, Optional

from django.db.models import Q

if TYPE_CHECKING:
    # Type-only: importing models at module load would cycle through apps that import this module.
    from programs.models import Program
    from screener.models import WhiteLabel

logger = logging.getLogger(__name__)

FEDERAL_WHITE_LABEL = "federal"


def visible_to(white_label: "WhiteLabel", prefix: str = "") -> Q:
    """Programs a screen under `white_label` sees: the white label's own plus the federal ones.

    `prefix` reaches the program through a relation, e.g. `prefix="program__"` on CurrentBenefit.
    """
    return Q(**{f"{prefix}white_label": white_label}) | Q(**{f"{prefix}white_label__code": FEDERAL_WHITE_LABEL})


def visible_to_code(white_label_code: str, prefix: str = "") -> Q:
    """`visible_to` for a white label code, optionally through a relation (`prefix="programs__"`)."""
    return Q(**{f"{prefix}white_label__code": white_label_code}) | Q(
        **{f"{prefix}white_label__code": FEDERAL_WHITE_LABEL}
    )


def is_federal(program: "Program") -> bool:
    return program.white_label.code == FEDERAL_WHITE_LABEL


def preferred_program(kept: Optional["Program"], candidate: "Program", where: str) -> "Program":
    """Of two programs with the same name, the one a screen should see.

    A query built with `visible_to` (a white label's own programs plus the federal ones) can
    match one name twice where a federal row is not prefixed. `kept` is the program already
    chosen for the name, or None when `candidate` is the first. The database allows one row
    per (white label, name), so a name never matches more than one state row and one federal
    row. The choice:

    - **An active row beats an inactive one.** Before a move the state row is live and a
      federal row may already exist inactive (the importer creates programs inactive); after
      it, the federal row is live and the state row is deactivated, not deleted. Either way
      the live row is the program.
    - **Between two rows in the same state, the federal one wins.** Both inactive covers
      callers that resolve benefits no longer offered. Both active means the state row was
      never deactivated; that is logged at ERROR (which reaches Sentry) with `where` naming the
      calling read path, rather than raised, so a stale row can't take a page down.

    Neither rule depends on which row arrives first, so query order can't change the result.
    Both programs must have `white_label` loaded (`select_related("white_label")`), or the
    comparison costs a query.
    """
    if kept is None:
        return candidate

    if kept.active != candidate.active:
        return kept if kept.active else candidate

    if kept.active:
        logger.error(
            "Program '%s' is active under both white labels '%s' and '%s' (%s); using the federal row. "
            "Deactivate the state row.",
            candidate.name_abbreviated,
            kept.white_label.code,
            candidate.white_label.code,
            where,
        )

    return candidate if is_federal(candidate) and not is_federal(kept) else kept


def filter_programs_by_name(programs: Iterable["Program"], where: str) -> list["Program"]:
    """`programs` with one program per name, chosen by `preferred_program`.

    For the result of a `visible_to` query, which every caller keys by `name_abbreviated`. The
    list keeps the order in which each name first appeared.
    """
    kept: dict[str, "Program"] = {}
    for program in programs:
        name = program.name_abbreviated
        kept[name] = preferred_program(kept.get(name), program, where)
    return list(kept.values())


def visible_program(white_label: "WhiteLabel", name_abbreviated: str, where: str) -> Optional["Program"]:
    """The program a screen under `white_label` sees by this name, or None.

    The white label's own row or the federal one, chosen by `preferred_program` when both exist.
    Inactive rows are included: a caller deciding whether a household holds a benefit has to
    resolve programs that are no longer offered.
    """
    from programs.models import Program

    candidates = Program.objects.filter(visible_to(white_label), name_abbreviated=name_abbreviated)

    program: Optional[Program] = None
    for candidate in candidates.select_related("white_label"):
        program = preferred_program(program, candidate, where)
    return program
