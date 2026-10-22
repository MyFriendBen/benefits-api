import logging

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

logger = logging.getLogger(__name__)

# The federal Child and Dependent Care Credit is one `federal_cdcc` row on the `federal` white
# label, which every white label sees. These are the per-state copies it replaces; a screen
# that marked one of them as a benefit it already has should now be holding the federal row.
# Kansas's own credit (`ks_cdcc`) is a separate program and is not listed.
STATE_FEDERAL_CDCC_ROWS = (
    ("ks", "ks_cdcc_federal"),
    ("mo", "mo_cdcc_federal"),
)
FEDERAL_ROW = ("federal", "federal_cdcc")


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Repoint "already has this benefit" rows from the state copies to `federal_cdcc`.

    Needs the federal row to exist, so it runs after the program record is imported. It fails
    closed: when the federal row is absent and state rows are waiting to move, it raises so
    the deploy stops rather than leaving them behind silently. When the federal row is absent
    and there is nothing to move (a fresh or test database), it logs and does nothing. A
    screen that already holds the federal row keeps it and its state row is deleted, since
    the table is unique on (screen, program). Re-running finds nothing left to move.
    """
    Program = apps.get_model("programs", "Program")
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")

    state_rows = [
        row
        for white_label_code, name_abbreviated in STATE_FEDERAL_CDCC_ROWS
        for row in CurrentBenefit.objects.filter(
            program__white_label__code=white_label_code, program__name_abbreviated=name_abbreviated
        )
    ]

    federal = Program.objects.filter(white_label__code=FEDERAL_ROW[0], name_abbreviated=FEDERAL_ROW[1]).first()
    if federal is None:
        if state_rows:
            raise RuntimeError(
                f"federal/federal_cdcc must be imported before this migration runs: {len(state_rows)} "
                "current-benefit rows on state CDCC rows are waiting to move (see PR #1837 Deployment step 2)"
            )
        logger.warning("federal/federal_cdcc does not exist and no current-benefit rows wait on it; nothing to move.")
        return

    for row in state_rows:
        if CurrentBenefit.objects.filter(screen_id=row.screen_id, program=federal).exists():
            row.delete()
        else:
            row.program = federal
            row.save(update_fields=["program"])


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0195_move_state_ctc_current_benefits"),
        ("screener", "0150_backfill_screen_current_benefits"),
    ]

    operations = [
        # No reverse: the state rows this moves off are deactivated and their calculators are
        # gone, so there is nothing to move back onto.
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
