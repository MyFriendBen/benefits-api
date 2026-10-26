from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# Federal EITC and SSDI are one `federal_eitc` / `federal_ssdi` row each on the `federal` white
# label, which every white label sees. These are the per-state rows they replace, switched off
# by 0193 and 0194. A household that said it already receives the benefit holds a
# CurrentBenefit row on its state's row; `already_has` on the results page is an exact-name
# match, so those rows are moved onto the federal row. The state rows are switched off, never
# deleted: CurrentBenefit.program cascades.
MOVES = {
    ("federal", "federal_eitc"): (
        ("co", "eitc"),
        ("co_tax_calculator", "eitc"),
        ("il", "eitc"),
        ("ma", "eitc"),
        ("nc", "eitc"),
        ("ks", "ks_eitc_federal"),
        ("mo", "mo_eitc"),
        ("tx", "tx_eitc"),
        ("wa", "wa_eitc"),
    ),
    ("federal", "federal_ssdi"): (
        ("co", "ssdi"),
        ("il", "ssdi"),
        ("ma", "ssdi"),
        ("nc", "ssdi"),
        ("cesn", "cesn_ssdi"),
        ("ks", "ks_ssdi"),
        ("mo", "mo_ssdi"),
        ("tx", "tx_ssdi"),
        ("wa", "wa_ssdi"),
    ),
}


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Move every CurrentBenefit row on a state EITC or SSDI row onto its federal row.

    Fails closed: when rows are waiting on a program's state rows and its federal row has not
    been imported, there is nothing to move them onto, so the migration raises rather than
    leaving them stranded on rows that are switched off. Both programs are checked before
    anything moves, so a failure leaves neither half-done. A database with no state rows
    either (fresh or test) has nothing to do and says so. A screen that already holds the
    federal row keeps that one and loses the state row, since (screen, program) is unique.
    Re-running finds no state rows and does nothing.
    """
    Program = apps.get_model("programs", "Program")
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")

    plans = []
    missing = []
    for (federal_code, federal_name), state_rows_spec in MOVES.items():
        state_program_ids = [
            program.id
            for white_label_code, name_abbreviated in state_rows_spec
            for program in Program.objects.filter(white_label__code=white_label_code, name_abbreviated=name_abbreviated)
        ]
        state_rows = CurrentBenefit.objects.filter(program_id__in=state_program_ids)
        federal = Program.objects.filter(white_label__code=federal_code, name_abbreviated=federal_name).first()
        if federal is None:
            waiting = state_rows.count()
            if waiting:
                missing.append(f"{federal_code}/{federal_name} ({waiting} rows waiting)")
            else:
                print(f"  {federal_code}/{federal_name} does not exist in this environment and no state rows hold current benefits")
            continue
        plans.append((federal_name, federal, state_rows))

    if missing:
        raise RuntimeError(
            "import these federal rows before this migration runs, current-benefit rows on their "
            f"state rows are waiting to move: {', '.join(missing)}"
        )

    for federal_name, federal, state_rows in plans:
        screens_already_federal = set(
            CurrentBenefit.objects.filter(program=federal, screen_id__in=state_rows.values("screen_id")).values_list(
                "screen_id", flat=True
            )
        )
        collapsed = state_rows.filter(screen_id__in=screens_already_federal).delete()[0]

        # One row per screen: a screen could hold two state rows, and both cannot become the
        # same federal row.
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

        print(f"  moved {moved} current-benefit rows onto {federal_name}; {collapsed} duplicates removed")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0197_navigator_email_no_auto"),
        ("screener", "0169_screen_household_size_range"),
    ]

    operations = [
        # No reverse: the state rows are off, so a row pointing at one would mark a benefit
        # nothing can show again.
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
