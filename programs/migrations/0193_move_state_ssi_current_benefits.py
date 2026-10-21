from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# Federal SSI is one `federal_ssi` row on the `federal` white label, which every white label
# sees. These are the per-state rows it replaces. A household that said it already receives
# SSI holds a CurrentBenefit row on its state's row; `already_has` on the results page is an
# exact-name match, so those rows are moved onto the federal row. The state rows themselves
# are switched off in the admin, never deleted: CurrentBenefit.program cascades.
STATE_SSI_ROWS = (
    ("co", "ssi"),
    ("il", "ssi"),
    ("ma", "ssi"),
    ("nc", "ssi"),
    ("cesn", "cesn_ssi"),
    ("ks", "ks_ssi"),
    ("mo", "mo_ssi"),
    ("tx", "tx_ssi"),
    ("wa", "wa_ssi"),
)

FEDERAL_SSI = ("federal", "federal_ssi")


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Move every CurrentBenefit row on a state SSI row onto `federal_ssi`.

    Does nothing when the federal row is absent: a fresh or test database has no programs
    at all, and an environment where the record has not been imported yet has nothing to
    move onto. Both are reported so the gap is visible. A screen that already holds the
    federal row keeps that one and loses the state row, since (screen, program) is unique.
    Re-running finds no state rows and does nothing.
    """
    Program = apps.get_model("programs", "Program")
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")

    federal = Program.objects.filter(white_label__code=FEDERAL_SSI[0], name_abbreviated=FEDERAL_SSI[1]).first()
    if federal is None:
        print("  federal/federal_ssi does not exist in this environment; no current-benefit rows moved")
        return

    state_program_ids = [
        program.id
        for white_label_code, name_abbreviated in STATE_SSI_ROWS
        for program in Program.objects.filter(white_label__code=white_label_code, name_abbreviated=name_abbreviated)
    ]
    state_rows = CurrentBenefit.objects.filter(program_id__in=state_program_ids)

    screens_already_federal = set(
        CurrentBenefit.objects.filter(program=federal, screen_id__in=state_rows.values("screen_id")).values_list(
            "screen_id", flat=True
        )
    )
    collapsed = state_rows.filter(screen_id__in=screens_already_federal).delete()[0]

    # One row per screen: a screen could hold two state rows (a derived `ssi` beside a ticked
    # `cesn_ssi`, say), and both cannot become the same federal row.
    moved = 0
    seen: set[int] = set()
    for row in state_rows.order_by("screen_id", "id"):
        if row.screen_id in seen:
            row.delete()
            collapsed += 1
            continue
        seen.add(row.screen_id)
        row.program = federal
        row.save(update_fields=["program"])
        moved += 1

    print(f"  moved {moved} current-benefit rows onto federal_ssi; {collapsed} duplicates removed")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0192_add_year_type_to_program"),
        ("screener", "0168_household_rows_default_id_ordering"),
    ]

    operations = [
        # No reverse: the state rows are off and their calculators gone, so a row pointing at
        # one would mark a benefit nothing can show again.
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
