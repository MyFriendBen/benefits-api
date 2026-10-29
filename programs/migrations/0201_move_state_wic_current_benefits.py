from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.models import Min

# Federal WIC is one `federal_wic` row on the `federal` white label, which every white label
# sees. These are the per-state rows it replaces. A household that said it already receives
# WIC holds a CurrentBenefit row on its state's row; `already_has` on the results page is an
# exact-name match, so those rows are moved onto the federal row. The state rows are then
# switched off and taken off the has-benefits step, never deleted: CurrentBenefit.program
# cascades, and their eligibility snapshots keep their history.
#
# This is the switch-over, so it also switches `federal_wic` on. The import can't create
# `federal_wic` until its calculator is deployed, and it creates programs switched off, so
# the federal row is imported in an earlier release and left off; switching it on here
# replaces the state rows in one step, with no window where WIC shows twice or not at all.
STATE_WIC_ROWS = (
    ("co", "co_wic"),
    # An older unprefixed CO row, inactive; staging and local databases still have it.
    ("co", "wic"),
    ("il", "il_wic"),
    ("ma", "ma_wic"),
    ("nc", "nc_wic"),
    ("cesn", "cesn_wic"),
    ("ks", "ks_wic"),
    ("mo", "mo_wic"),
    ("tx", "tx_wic"),
    ("wa", "wa_wic"),
)

FEDERAL_WIC = ("federal", "federal_wic")


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Move every CurrentBenefit row on a state WIC row onto `federal_wic`, switch the state
    rows off and `federal_wic` on.

    Fails closed, before anything changes, when `federal_wic` hasn't been imported but WIC is
    live on a state row (switched on, or holding a household's current benefit): there would
    be nothing to replace it with. A database with no live state rows and no federal row
    (fresh or test) changes nothing and says so. A screen that already holds the federal row
    keeps that one and loses the state row, since (screen, program) is unique. Re-running
    finds nothing to move or switch.
    """
    Program = apps.get_model("programs", "Program")
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")

    state_programs = Program.objects.none()
    for white_label_code, name_abbreviated in STATE_WIC_ROWS:
        state_programs |= Program.objects.filter(white_label__code=white_label_code, name_abbreviated=name_abbreviated)
    state_rows = CurrentBenefit.objects.filter(program__in=state_programs)
    live_state_rows = state_programs.filter(active=True).count()

    federal = Program.objects.filter(white_label__code=FEDERAL_WIC[0], name_abbreviated=FEDERAL_WIC[1]).first()
    if federal is None:
        waiting = state_rows.count()
        if waiting or live_state_rows:
            raise RuntimeError(
                f"federal/federal_wic must be imported before this migration runs: {live_state_rows} state WIC "
                f"rows are switched on and {waiting} current-benefit rows are waiting to move. Import it with "
                "program-ops' scripts/import_programs.py --program federal_wic, then migrate again."
            )
        print("  no federal/federal_wic and no live state WIC rows in this environment; nothing to do")
        return

    screens_already_federal = CurrentBenefit.objects.filter(
        program=federal, screen_id__in=state_rows.values("screen_id")
    ).values("screen_id")
    collapsed = state_rows.filter(screen_id__in=screens_already_federal).delete()[0]

    # One row per screen: a screen could hold two state rows, and both cannot become the
    # same federal row. Keep each screen's first and move the survivors in one UPDATE.
    first_per_screen = state_rows.values("screen_id").annotate(first_id=Min("id")).values("first_id")
    collapsed += state_rows.exclude(id__in=first_per_screen).delete()[0]
    moved = state_rows.update(program=federal)

    switched_off = state_programs.filter(active=True).update(active=False)
    hidden = state_programs.filter(show_in_has_benefits_step=True).update(show_in_has_benefits_step=False)
    # Only where WIC was live: an environment that had WIC switched off everywhere keeps it off.
    switched_on = bool(live_state_rows) and not federal.active
    if switched_on:
        Program.objects.filter(id=federal.id).update(active=True)

    print(
        f"  moved {moved} current-benefit rows onto federal_wic; {collapsed} duplicates removed; "
        f"switched off {switched_off} state WIC rows and took {hidden} off the has-benefits step; "
        f"federal_wic {'switched on' if switched_on else 'left as it was (active=' + str(federal.active) + ')'}"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0200_retire_state_federal_program_rows"),
        ("screener", "0169_screen_household_size_range"),
    ]

    operations = [
        # Irreversible: unapplying it can't put moved households back on their state rows or
        # restore the duplicate rows it removed, so `migrate` refuses rather than appearing to
        # roll back. To stop serving federal WIC, switch the state rows on and `federal_wic` off
        # in the admin; the moved households then show WIC as new until moved back by hand.
        migrations.RunPython(forwards),
    ]
