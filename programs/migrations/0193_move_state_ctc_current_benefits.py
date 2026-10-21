from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

from programs.current_benefits_moves import STATE_ROWS_BY_FEDERAL_PROGRAM, move_current_benefits

# The federal Child Tax Credit is one `federal_ctc` row on the `federal` white label, which
# every white label sees. "Already has CTC" rows on the nine state copies it replaces move
# onto it. Without a `federal_ctc` row (a fresh or test database, or an environment where the
# record has not been imported yet) nothing is touched; `manage.py move_state_current_benefits
# federal_ctc` finishes the move once it exists.
FEDERAL_PROGRAM = "federal_ctc"


def move_ctc_current_benefits(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    move_current_benefits(
        apps.get_model("programs", "Program"),
        apps.get_model("screener", "WhiteLabel"),
        apps.get_model("screener", "CurrentBenefit"),
        FEDERAL_PROGRAM,
        STATE_ROWS_BY_FEDERAL_PROGRAM[FEDERAL_PROGRAM],
    )


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
