"""
Shared fixtures for tests that exercise Screen.has_benefit() — which now reads
from the CurrentBenefit join table. Use seed_program() to create the Program
row a join-table lookup will need, then call sync_current_benefits() after
setting has_* columns (mirroring what the serializer does on every POST/PATCH).

Lifecycle: both helpers are transitional and will be removed in MFB-720 once
the has_* columns are gone and tests write CurrentBenefit rows directly via
the new `current_benefits: [...]` serializer payload.
"""

from programs.models import Program
from screener.models import Screen, WhiteLabel
from screener.serializers import _write_current_benefits


def seed_program(white_label: WhiteLabel, *name_abbreviateds: str) -> None:
    """Create one or more Programs (with required Translation FKs) so the
    join-table read path can resolve `program__name_abbreviated=name`. Thin
    wrapper around the canonical `Program.objects.new_program` manager method."""
    for name in name_abbreviateds:
        Program.objects.new_program(white_label.code, name)


def set_current_benefits(screen: Screen, *name_abbreviateds: str) -> None:
    """Write CurrentBenefit join-table rows directly for `screen`, exercising the
    primary write path (Step 5a / MFB-869) instead of the legacy
    `has_* = True; sync_current_benefits()` mirror.

    Delegates to the serializer's `_write_current_benefits()` with an explicit
    `current_benefits` list — the same branch a new-frontend PATCH takes. Each
    name must already exist as a Program in the screen's white label (call
    `seed_program()` first). Replaces any existing rows for the screen.
    """
    _write_current_benefits(screen, list(name_abbreviateds))


def sync_current_benefits(screen: Screen) -> None:
    """Mirror the serializer's backward-compat write: rebuild CurrentBenefit rows
    from the current has_* column state on `screen`.

    Delegates to the serializer's `_write_current_benefits(..., current_benefits=None)`
    backward-compat branch — the same code path an old-frontend PATCH takes — so the
    helper can't drift from production behavior. Tests that still set has_* columns
    and call this remain valid until Step 6 (MFB-720) drops the has_* write path and
    removes both the helper and the has_* branch.
    """
    _write_current_benefits(screen, None)
