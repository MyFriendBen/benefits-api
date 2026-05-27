"""
Shared fixtures for tests that exercise Screen.has_benefit() — which now reads
from the ScreenCurrentBenefit join table. Use seed_program() to create the
Program row a join-table lookup will need, then call sync_current_benefits()
after setting has_* columns (mirroring the serializer dual-write).
"""

from programs.models import Program
from screener.models import Screen, WhiteLabel
from screener.serializers import _sync_current_benefits
from translations.models import Translation


REQUIRED_TRANSLATION_FIELDS = (
    "name",
    "description_short",
    "description",
    "learn_more_link",
    "apply_button_link",
    "apply_button_description",
    "estimated_delivery_time",
    "estimated_application_time",
    "estimated_value",
    "website_description",
)


def seed_program(white_label: WhiteLabel, name_abbreviated: str, **overrides) -> Program:
    """Create a Program with all required Translation FKs filled. Used so the
    join-table read path can resolve `program__name_abbreviated=name`."""
    label = f"seed-{white_label.code}-{name_abbreviated}"
    defaults = {
        field: Translation.objects.add_translation(f"program.{label}-{field}", default_message="")
        for field in REQUIRED_TRANSLATION_FIELDS
    }
    defaults.update(
        white_label=white_label,
        name_abbreviated=name_abbreviated,
        external_name=label,
        active=True,
        show_in_has_benefits_step=True,
    )
    defaults.update(overrides)
    return Program.objects.create(**defaults)


def sync_current_benefits(screen: Screen) -> None:
    """Mirror what the serializer does on every POST/PATCH — write join-table
    rows reflecting the current has_* column state."""
    _sync_current_benefits(screen)
