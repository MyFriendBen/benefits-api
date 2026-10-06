"""
Federal programs: one `Program` row under the `federal` white label, shown to every white
label instead of a copy per state.

A federal row reuses the `name_abbreviated` of the calculator it runs, which is the same
name the state rows it replaces carry. Each program's move deactivates those state rows, so
an *active* name under both `federal` and a state white label is a configuration error. The
import command and `audit_federal_programs` fail on one. The read paths here log it and let
the federal row win instead, because a stale row must not take a results page down with it.

An *inactive* state row sharing a federal row's name is the expected state after a move (rows
are deactivated, not deleted, to keep snapshot history), so preferring the federal row there
is silent.
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


def active_duplicates(names: Optional[Iterable[str]] = None) -> dict[str, list[str]]:
    """Names active under both `federal` and another white label: `{name: [other codes]}`.

    Limited to `names` when given. Empty means the configuration is clean.
    """
    from programs.models import Program

    active = Program.objects.filter(active=True)
    if names is not None:
        active = active.filter(name_abbreviated__in=list(names))

    federal_names = set(active.filter(white_label__code=FEDERAL_WHITE_LABEL).values_list("name_abbreviated", flat=True))
    duplicates: dict[str, list[str]] = {}
    rows = (
        active.filter(name_abbreviated__in=federal_names)
        .exclude(white_label__code=FEDERAL_WHITE_LABEL)
        .values_list("name_abbreviated", "white_label__code")
        .order_by("name_abbreviated", "white_label__code")
    )
    for name, code in rows:
        duplicates.setdefault(name, []).append(code)
    return duplicates


def conflicting_active_programs(white_label_code: str, name_abbreviated: str) -> list["Program"]:
    """Active programs that a program under `white_label_code` can't be active alongside.

    For a federal program, the active state rows of the same name; for a state program, the
    active federal row. Ordered by white label code, with `white_label` loaded.
    """
    from programs.models import Program

    active = Program.objects.filter(name_abbreviated=name_abbreviated, active=True).select_related("white_label")
    if white_label_code == FEDERAL_WHITE_LABEL:
        active = active.exclude(white_label__code=FEDERAL_WHITE_LABEL)
    else:
        active = active.filter(white_label__code=FEDERAL_WHITE_LABEL)
    return list(active.order_by("white_label__code"))


def preferred_program(kept: Optional["Program"], candidate: "Program", where: str) -> "Program":
    """Of two programs with the same name, the one a screen should see.

    A federal program reuses the name of the state rows it replaced, so a query built with
    `visible_to` (a white label's own programs plus the federal ones) can match one name twice.
    `kept` is the program already chosen for the name, or None when `candidate` is the first.
    The database allows one row per (white label, name), so a name never matches more than one
    state row and one federal row. The choice:

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
            "Run audit_federal_programs and deactivate the state row.",
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
