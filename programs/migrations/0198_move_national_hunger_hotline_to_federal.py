from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# Navigators are shared by `external_name`, so a navigator belongs to whichever white label
# imported it first. USDA's National Hunger Hotline is national, but MO's SNAP and NSLP
# configs created it, so it sits on `mo`. Federal WIC links the same row, and on a federal
# program only `federal` navigators and the screen's own white label's are shown, so on
# `mo` it would reach MO households only. Moving it to `federal` changes nothing for MO's
# programs: navigators on a state program are not filtered by white label.
NAVIGATOR = "usda_national_hunger_hotline"


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Navigator = apps.get_model("programs", "Navigator")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")

    federal = WhiteLabel.objects.filter(code="federal").first()
    if federal is None:
        print("  no federal white label in this environment; nothing to move")
        return

    moved = Navigator.objects.filter(external_name=NAVIGATOR).exclude(white_label=federal).update(white_label=federal)
    print(f"  moved {moved} navigator rows named {NAVIGATOR} to the federal white label")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0197_navigator_email_no_auto"),
    ]

    operations = [
        # No reverse: the white label it came from differs by environment.
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
