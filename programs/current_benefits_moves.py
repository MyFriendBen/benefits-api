"""Move "already has" rows from retired state program rows onto their federal replacement.

A `CurrentBenefit` row points at a `Program`. When a program moves to the federal white
label, the households that ticked a state row have to point at the federal one or the
credit shows as new. The same move runs from a data migration (with historical models)
and from the `move_state_current_benefits` command (with the real ones), so the logic
takes its models as arguments.
"""

from dataclasses import dataclass
from typing import Callable, Iterable

FEDERAL_WHITE_LABEL = "federal"

#: The state rows each federal program replaced, keyed by the federal program's name and
#: matched by (white label code, name_abbreviated). Never by `base_program`: the states'
#: own credits (`coctc`, `il_ctc`, `ma_cfc`) share `base_program = ctc` and are separate
#: programs.
STATE_ROWS_BY_FEDERAL_PROGRAM: dict[str, tuple[tuple[str, str], ...]] = {
    "federal_ctc": (
        ("co", "ctc"),
        ("co_tax_calculator", "ctc"),
        ("il", "ctc"),
        ("ma", "ctc"),
        ("nc", "ctc"),
        ("ks", "ks_ctc"),
        ("mo", "mo_ctc"),
        ("tx", "tx_ctc"),
        ("wa", "wa_ctc"),
    ),
}


@dataclass(frozen=True)
class MoveResult:
    #: Whether the federal row existed. When False nothing was touched.
    federal_found: bool
    moved: int = 0
    #: State rows dropped because the screen already held the federal row.
    duplicates_dropped: int = 0


def move_current_benefits(
    Program,
    WhiteLabel,
    CurrentBenefit,
    federal_program: str,
    state_rows: Iterable[tuple[str, str]],
    out: Callable[[str], None] = print,
) -> MoveResult:
    """Repoint every CurrentBenefit on one of `state_rows` at `federal`/`federal_program`.

    A screen already holding the federal row keeps it and loses the state row, since
    (screen, program) is unique. Without a federal row nothing is touched and the caller
    is told; a state row absent from the environment is skipped. Running it again finds
    nothing to move.
    """
    federal = Program.objects.filter(white_label__code=FEDERAL_WHITE_LABEL, name_abbreviated=federal_program).first()
    if federal is None:
        out(f"  {FEDERAL_WHITE_LABEL}/{federal_program}: not in this environment, nothing moved")
        return MoveResult(federal_found=False)

    moved = dropped = 0
    for white_label_code, name_abbreviated in state_rows:
        white_label = WhiteLabel.objects.filter(code=white_label_code).first()
        if white_label is None:
            continue
        state = Program.objects.filter(white_label=white_label, name_abbreviated=name_abbreviated).first()
        if state is None:
            continue
        if state.pk == federal.pk:
            # Naming the target as a source would match every federal row as a "duplicate"
            # and delete it before the update ran.
            out(f"  {white_label_code}/{name_abbreviated}: is the federal row itself, skipped")
            continue

        screens_on_federal = CurrentBenefit.objects.filter(program=federal).values_list("screen_id", flat=True)
        duplicates = CurrentBenefit.objects.filter(program=state, screen_id__in=screens_on_federal)
        dropped_here = duplicates.delete()[0]
        moved_here = CurrentBenefit.objects.filter(program=state).update(program=federal)
        dropped += dropped_here
        moved += moved_here
        out(f"  {white_label_code}/{name_abbreviated}: {moved_here} moved, {dropped_here} duplicate(s) dropped")

    out(f"  {federal_program}: {moved} current-benefit row(s) moved, {dropped} duplicate(s) dropped")
    return MoveResult(federal_found=True, moved=moved, duplicates_dropped=dropped)
