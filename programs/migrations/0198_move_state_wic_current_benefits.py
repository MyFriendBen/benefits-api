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
    """Move every CurrentBenefit row on a state WIC row onto `federal_wic`, then switch the
    state rows off.

    Fails closed, before anything changes:
    - rows are waiting on the state WIC rows and the federal row has not been imported, so
      there is nothing to move them onto;
    - the federal row exists but is switched off, so switching the state rows off would
      leave no WIC on any white label. The import creates programs switched off, so
      `federal_wic` is switched on in the admin before this runs.
    A database with neither the federal row nor any waiting rows (fresh, test, or a local
    database that never imported it) changes nothing and says so; its state rows stay on.
    A screen that already holds the federal row keeps that one and loses the state row,
    since (screen, program) is unique. Re-running finds nothing to move or switch off.
    """
    Program = apps.get_model("programs", "Program")
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")

    state_programs = Program.objects.none()
    for white_label_code, name_abbreviated in STATE_WIC_ROWS:
        state_programs |= Program.objects.filter(white_label__code=white_label_code, name_abbreviated=name_abbreviated)
    state_rows = CurrentBenefit.objects.filter(program__in=state_programs)

    federal = Program.objects.filter(white_label__code=FEDERAL_WIC[0], name_abbreviated=FEDERAL_WIC[1]).first()
    if federal is None:
        waiting = state_rows.count()
        if waiting:
            raise RuntimeError(
                f"federal/federal_wic must be imported before this migration runs: {waiting} current-benefit "
                "rows on state WIC rows are waiting to move (see the PR's Deployment section)"
            )
        print("  federal/federal_wic does not exist in this environment; state WIC rows left as they are")
        return
    if not federal.active and state_programs.filter(active=True).exists():
        raise RuntimeError(
            "federal/federal_wic must be switched on in the admin before this migration runs: it switches "
            "the state WIC rows off, which would leave no WIC on any white label (see the PR's Deployment section)"
        )

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

    print(
        f"  moved {moved} current-benefit rows onto federal_wic; {collapsed} duplicates removed; "
        f"switched off {switched_off} state WIC rows and took {hidden} off the has-benefits step"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0197_navigator_email_no_auto"),
        ("screener", "0169_screen_household_size_range"),
    ]

    operations = [
        # No reverse: switching the state rows back on beside an active `federal_wic` would
        # show WIC twice, and some were off before this ran. Roll back in the admin.
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
