"""
Shared fixtures for tests that exercise Screen.has_benefit() — which now reads
from the ScreenCurrentBenefit join table. Use seed_program() to create the
Program row a join-table lookup will need, then call sync_current_benefits()
after setting has_* columns (mirroring the serializer dual-write).
"""

from programs.models import Program
from screener.models import Screen, WhiteLabel
from screener.serializers import _sync_current_benefits


def seed_program(white_label: WhiteLabel, name_abbreviated: str) -> Program:
    """Create a Program (with required Translation FKs) so the join-table read
    path can resolve `program__name_abbreviated=name`. Thin wrapper around the
    canonical `Program.objects.new_program` manager method."""
    return Program.objects.new_program(white_label.code, name_abbreviated)


def sync_current_benefits(screen: Screen) -> None:
    """Mirror what the serializer does on every POST/PATCH — write join-table
    rows reflecting the current has_* column state."""
    _sync_current_benefits(screen)
