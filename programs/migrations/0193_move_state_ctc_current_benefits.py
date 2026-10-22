from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# The federal Child Tax Credit is one `federal_ctc` row on the `federal` white label, which
# every white label sees. "Already has CTC" is a CurrentBenefit row pointing at a program,
# so households that ticked one of the nine state copies it replaces have to point at the
# federal row, or the credit shows as new. Rows are matched by (white label, name), never by
# `base_program`: the states' own credits `coctc`, `il_ctc` and `ma_cfc` carry
# `base_program = ctc` and are separate programs.
#
# Without a `federal_ctc` row (a fresh or test database, or an environment where the record
# has not been imported yet) nothing is touched; re-running `move_ctc_current_benefits` from
# a shell with the real app registry finishes the move once it exists.
FEDERAL_WHITE_LABEL = "federal"
FEDERAL_PROGRAM = "federal_ctc"
STATE_FEDERAL_CTC_ROWS = (
    ("co", "ctc"),
    ("co_tax_calculator", "ctc"),
    ("il", "ctc"),
    ("ma", "ctc"),
    ("nc", "ctc"),
    ("ks", "ks_ctc"),
    ("mo", "mo_ctc"),
    ("tx", "tx_ctc"),
    ("wa", "wa_ctc"),
)


def move_ctc_current_benefits(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Repoint every CurrentBenefit on a state CTC row at `federal`/`federal_ctc`.

    A screen already holding the federal row keeps it and loses the state row, since
    (screen, program) is unique. A state row absent from the environment is skipped, as is
    one that resolves to the federal program itself. Running it again finds nothing to move.
    """
    Program = apps.get_model("programs", "Program")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")

    federal = Program.objects.filter(white_label__code=FEDERAL_WHITE_LABEL, name_abbreviated=FEDERAL_PROGRAM).first()
    if federal is None:
        print(f"  {FEDERAL_WHITE_LABEL}/{FEDERAL_PROGRAM}: not in this environment, nothing moved")
        return

    moved = dropped = 0
    for white_label_code, name_abbreviated in STATE_FEDERAL_CTC_ROWS:
        white_label = WhiteLabel.objects.filter(code=white_label_code).first()
        if white_label is None:
            continue
        state = Program.objects.filter(white_label=white_label, name_abbreviated=name_abbreviated).first()
        if state is None:
            continue
        if state.pk == federal.pk:
            # Naming the target as a source would match every federal row as a "duplicate"
            # and delete it before the update ran.
            print(f"  {white_label_code}/{name_abbreviated}: is the federal row itself, skipped")
            continue

        # Refreshed each pass on purpose: a screen moved onto the federal row by an earlier
        # state row is a duplicate for a later one, and is dropped rather than moved twice.
        screens_on_federal = CurrentBenefit.objects.filter(program=federal).values_list("screen_id", flat=True)
        duplicates = CurrentBenefit.objects.filter(program=state, screen_id__in=screens_on_federal)
        dropped_here = duplicates.delete()[0]
        moved_here = CurrentBenefit.objects.filter(program=state).update(program=federal)
        dropped += dropped_here
        moved += moved_here
        print(f"  {white_label_code}/{name_abbreviated}: {moved_here} moved, {dropped_here} duplicate(s) dropped")

    print(f"  {FEDERAL_PROGRAM}: {moved} current-benefit row(s) moved, {dropped} duplicate(s) dropped")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0192_add_year_type_to_program"),
        ("screener", "0148_add_currentbenefit"),
    ]

    operations = [
        # No reverse: which state row a household came from is not recorded, and the state
        # rows are off for good.
        migrations.RunPython(move_ctc_current_benefits, migrations.RunPython.noop),
    ]
