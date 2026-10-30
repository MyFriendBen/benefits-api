from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# Navigators are shared by `external_name`, so a navigator belongs to whichever white label
# imported it first. On a federal program only `federal` navigators and those of the screen's
# state are shown, so a national navigator owned by one state would reach that state only.
# Moving these to `federal` changes nothing for the state programs that also link them:
# navigators on a state program are not filtered by white label.
#
# - `usda_national_hunger_hotline`: MO's SNAP and NSLP configs created it, so it sits on `mo`,
#   and federal WIC links it.
# - `trump_account_call_center`: on `mo` in production and linked to the active
#   `federal_trump_account`. The import would move it, since that program's record owns it,
#   but imports run by hand after a deploy; moving it here leaves no gap where only MO
#   households see it.
NAVIGATORS = ("usda_national_hunger_hotline", "trump_account_call_center")


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Navigator = apps.get_model("programs", "Navigator")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    federal = WhiteLabel.objects.filter(code="federal").first()
    if federal is None:
        print("  no federal white label in this environment; nothing to move")
        return

    for name in NAVIGATORS:
        moved = Navigator.objects.filter(external_name=name).exclude(white_label=federal).update(white_label=federal)
        print(f"  moved {moved} navigator rows named {name} to the federal white label")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0201_move_state_wic_current_benefits"),
    ]

    operations = [
        # No reverse: the white label each came from differs by environment.
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
