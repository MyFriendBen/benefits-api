"""
Shared fixtures for tests that exercise Screen.has_benefit() — which now reads
from the CurrentBenefit join table. Use seed_program() to create the Program
row a join-table lookup will need, then call sync_current_benefits() after
setting has_* columns (mirroring what the serializer does on every POST/PATCH).

Lifecycle: both helpers are transitional and will be removed in MFB-720 once
the has_* columns are gone and tests write CurrentBenefit rows directly via
the new `current_benefits: [...]` serializer payload.
"""

from django.db import transaction

from programs.models import Program
from screener.models import CurrentBenefit, Screen, WhiteLabel


def seed_program(white_label: WhiteLabel, *name_abbreviateds: str) -> None:
    """Create one or more Programs (with required Translation FKs) so the
    join-table read path can resolve `program__name_abbreviated=name`. Thin
    wrapper around the canonical `Program.objects.new_program` manager method."""
    for name in name_abbreviateds:
        Program.objects.new_program(white_label.code, name)


def sync_current_benefits(screen: Screen) -> None:
    """Mirror the serializer's dual-write: rebuild CurrentBenefit rows from the
    current has_* column state on `screen`.

    Body is intentionally inlined (rather than calling screener.serializers.
    _sync_current_benefits) so this helper survives MFB-869, which deletes the
    serializer function. The helper itself is deleted in MFB-720 once tests
    can write join-table rows directly.
    """
    with transaction.atomic():
        screen = Screen.objects.select_for_update().get(pk=screen.pk)
        benefit_map = screen._build_benefit_map()
        program_ids_to_write = [
            program.id
            for program in Program.objects.filter(white_label=screen.white_label)
            if benefit_map.get(program.name_abbreviated, False)
        ]
        CurrentBenefit.objects.filter(screen=screen).delete()
        if program_ids_to_write:
            CurrentBenefit.objects.bulk_create(
                [CurrentBenefit(screen=screen, program_id=pid) for pid in program_ids_to_write]
            )
