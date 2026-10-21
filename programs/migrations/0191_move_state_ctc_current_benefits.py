from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# The federal Child Tax Credit is one `federal_ctc` row on the `federal` white label, which
# every white label sees. These are the per-state copies it replaces. "Already has CTC" is a
# CurrentBenefit row pointing at a program, so a household that ticked a state row has to
# point at the federal one, or the credit shows as new. Rows are matched by (white label,
# name), never by `base_program`: the state credits `coctc`, `il_ctc` and `ma_cfc` carry
# `base_program = ctc` and are separate programs.
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

FEDERAL_WHITE_LABEL = "federal"
FEDERAL_PROGRAM = "federal_ctc"


def move_current_benefits(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Repoint every CurrentBenefit on a state CTC row at `federal_ctc`.

    A screen already holding the federal row keeps it and loses the state row, since
    (screen, program) is unique. Without a `federal_ctc` row (a fresh or test database, or an
    environment where the record has not been imported yet) nothing is touched: the rows
    then have to be moved by hand once it exists.
    """
    Program = apps.get_model("programs", "Program")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    CurrentBenefit = apps.get_model("screener", "CurrentBenefit")

    federal = Program.objects.filter(
        white_label__code=FEDERAL_WHITE_LABEL, name_abbreviated=FEDERAL_PROGRAM
    ).first()
    if federal is None:
        print(f"  {FEDERAL_WHITE_LABEL}/{FEDERAL_PROGRAM}: not in this environment, skipping the current-benefit move")
        return

    moved = deleted = 0
    for white_label_code, name_abbreviated in STATE_FEDERAL_CTC_ROWS:
        white_label = WhiteLabel.objects.filter(code=white_label_code).first()
        if white_label is None:
            continue
        state = Program.objects.filter(white_label=white_label, name_abbreviated=name_abbreviated).first()
        if state is None:
            continue

        screens_on_federal = CurrentBenefit.objects.filter(program=federal).values_list("screen_id", flat=True)
        duplicates = CurrentBenefit.objects.filter(program=state, screen_id__in=screens_on_federal)
        deleted += duplicates.delete()[0]
        moved += CurrentBenefit.objects.filter(program=state).update(program=federal)

    print(f"  {FEDERAL_PROGRAM}: {moved} current-benefit row(s) moved, {deleted} duplicate(s) dropped")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0190_add_denver_public_schools_referrer"),
        ("screener", "0148_add_currentbenefit"),
    ]

    operations = [
        # No reverse: which state row a household came from is not recorded, and the state
        # rows are off for good.
        migrations.RunPython(move_current_benefits, migrations.RunPython.noop),
    ]
