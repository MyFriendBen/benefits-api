"""
Shared fixtures for tests that exercise Screen.has_benefit() — which reads from
the CurrentBenefit join table. Use seed_program() to create the Program row a
join-table lookup will need, then write CurrentBenefit rows directly (or via the
`current_benefits: [...]` serializer payload) for the screen under test.
"""

from programs.models import Program
from screener.models import WhiteLabel


def seed_program(white_label: WhiteLabel, *name_abbreviateds: str) -> None:
    """Create one or more Programs (with required Translation FKs) so the
    join-table read path can resolve `program__name_abbreviated=name`. Thin
    wrapper around the canonical `Program.objects.new_program` manager method."""
    for name in name_abbreviateds:
        Program.objects.new_program(white_label.code, name)
