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
from typing import Iterable, Optional, TypeVar

from django.db.models import Q

logger = logging.getLogger(__name__)

FEDERAL_WHITE_LABEL = "federal"

T = TypeVar("T")


def visible_to(white_label) -> Q:
    """Programs a screen under `white_label` sees: the white label's own plus the federal ones."""
    return Q(white_label=white_label) | Q(white_label__code=FEDERAL_WHITE_LABEL)


def visible_to_code(white_label_code: str, prefix: str = "") -> Q:
    """`visible_to` for a white label code, optionally through a relation (`prefix="programs__"`)."""
    return Q(**{f"{prefix}white_label__code": white_label_code}) | Q(
        **{f"{prefix}white_label__code": FEDERAL_WHITE_LABEL}
    )


def is_federal(program) -> bool:
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


def one_per_name(programs: Iterable[T], where: str) -> list[T]:
    """Drop the state row wherever a federal row has the same name.

    For a query built with `visible_to`, which returns a white label's own programs plus the
    federal ones. A federal program reuses the name of the state rows it replaced, so one name
    can match two rows: the white label's and the federal one. Every caller keys programs by
    name, so it must see only one, and it should be the federal one.

    The database allows one row per (white label, name), so a name matches at most those two
    rows. The federal row wins whatever order the rows arrive in, which makes the result
    independent of the query's ordering; the returned list keeps the order in which each name
    first appeared.

    `where` names the calling read path for the log. The two rows are expected when the state
    row is inactive: its program moved to federal and the row was deactivated, not deleted. If
    both are active, the program was never deactivated on the state side; that is logged at
    ERROR (which reaches Sentry) rather than raised, so a stale row can't take a page down.

    Rows must have `white_label` loaded (`select_related("white_label")`), or each comparison
    costs a query.
    """
    kept: dict[str, T] = {}
    for program in programs:
        name = program.name_abbreviated
        current = kept.get(name)
        if current is None:
            kept[name] = program
            continue

        if current.active and program.active:
            logger.error(
                "Program '%s' is active under both white labels '%s' and '%s' (%s); using the federal row. "
                "Run audit_federal_programs and deactivate the state row.",
                name,
                current.white_label.code,
                program.white_label.code,
                where,
            )

        if is_federal(program) and not is_federal(current):
            kept[name] = program

    return list(kept.values())


def visible_program(white_label, name_abbreviated: str, where: str):
    """The one program a screen under `white_label` sees by this name, or None.

    The white label's own row or the federal one, the federal row winning when both exist
    (see `one_per_name`). Inactive rows are included: a caller deciding whether a household
    holds a benefit has to resolve programs that are no longer offered.
    """
    from programs.models import Program

    programs = one_per_name(
        Program.objects.filter(visible_to(white_label), name_abbreviated=name_abbreviated).select_related(
            "white_label"
        ),
        where,
    )
    return programs[0] if programs else None
