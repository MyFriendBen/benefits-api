from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models import Min

# Federal CDCC is one `federal_cdcc` row on the `federal` white label, which every white label
# sees. These are the two per-state rows it replaces. A household that said it already
# receives the credit holds a CurrentBenefit row on its state's row; `already_has` on the
# results page is an exact-name match, so those rows are moved onto the federal row. The
# state rows are then switched off and taken off the has-benefits step, never deleted:
# CurrentBenefit.program cascades, and their eligibility snapshots keep their history.
#
# `ks_cdcc` is deliberately NOT here. It is Kansas's own state credit, a different program
# with its own calculator, and it stays live. The two names differ by one suffix.
#
# This is the switch-over, so it also switches `federal_cdcc` on. The import creates programs
# switched off, so the federal row is imported before this migration and left off; switching
# it on here replaces the state rows in one step, with no window where CDCC shows twice or
# not at all.
STATE_CDCC_ROWS = (
    ("ks", "ks_cdcc_federal"),
    ("mo", "mo_cdcc_federal"),
)

FEDERAL_CDCC = ("federal", "federal_cdcc")


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Move every CurrentBenefit row on a state CDCC row onto `federal_cdcc`, switch the state
    rows off and `federal_cdcc` on.

    Fails closed, before anything changes, when `federal_cdcc` hasn't been imported but CDCC is
    live on a state row (switched on, or holding a household's current benefit): there would
    be nothing to replace it with. A database with no live state rows and no federal row
    (fresh or test) changes nothing and says so. A screen that already holds the federal row
    keeps that one and loses the state row, since (screen, program) is unique. Re-running
    finds nothing to move or switch.
    """
    Program = apps.get_model("programs", "Program")
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")

    state_programs = Program.objects.none()
    for white_label_code, name_abbreviated in STATE_CDCC_ROWS:
        state_programs |= Program.objects.filter(white_label__code=white_label_code, name_abbreviated=name_abbreviated)
    state_rows = CurrentBenefit.objects.filter(program__in=state_programs)
    live_state_rows = state_programs.filter(active=True).count()

    federal = Program.objects.filter(white_label__code=FEDERAL_CDCC[0], name_abbreviated=FEDERAL_CDCC[1]).first()
    if federal is None:
        waiting = state_rows.count()
        if waiting or live_state_rows:
            raise RuntimeError(
                f"federal/federal_cdcc must be imported before this migration runs: {live_state_rows} state CDCC "
                f"rows are switched on and {waiting} current-benefit rows are waiting to move. Import it with "
                "program-ops' scripts/import_programs.py --env <staging|prod> --program federal_cdcc, then migrate again."
            )
        print("  no federal/federal_cdcc and no live state CDCC rows in this environment; nothing to do")
        return

    screens_already_federal = CurrentBenefit.objects.filter(
        program=federal, screen_id__in=state_rows.values("screen_id")
    ).values("screen_id")
    collapsed = state_rows.filter(screen_id__in=screens_already_federal).delete()[0]

    # One row per screen: a screen could hold both state rows, and both cannot become the
    # same federal row. Keep each screen's first and move the survivors in one UPDATE.
    first_per_screen = state_rows.values("screen_id").annotate(first_id=Min("id")).values("first_id")
    collapsed += state_rows.exclude(id__in=first_per_screen).delete()[0]
    moved = state_rows.update(program=federal)

    switched_off = state_programs.filter(active=True).update(active=False)
    hidden = state_programs.filter(show_in_has_benefits_step=True).update(show_in_has_benefits_step=False)
    # Only where CDCC was live: an environment that had it switched off on the state rows
    # keeps the federal row off, to be switched on in the admin.
    switched_on = bool(live_state_rows) and not federal.active
    if switched_on:
        Program.objects.filter(id=federal.id).update(active=True)

    print(
        f"  moved {moved} current-benefit rows onto federal_cdcc; {collapsed} duplicates removed; "
        f"switched off {switched_off} state CDCC rows and took {hidden} off the has-benefits step; "
        f"federal_cdcc {'switched on' if switched_on else 'left as it was (active=' + str(federal.active) + ')'}"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0204_move_national_navigator_copies_to_federal"),
        ("screener", "0169_screen_household_size_range"),
    ]

    operations = [
        # Irreversible: unapplying it can't put moved households back on their state rows or
        # restore the duplicate rows it removed, so `migrate` refuses rather than appearing to
        # roll back. To stop serving federal CDCC, switch the state rows on and `federal_cdcc`
        # off in the admin; the moved households then show CDCC as new until moved back by hand.
        migrations.RunPython(forwards),
    ]
