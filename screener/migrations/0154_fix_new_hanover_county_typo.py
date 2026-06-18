from django.db import migrations


def fix_new_hanover_county_typo(apps, schema_editor) -> None:
    Screen = apps.get_model("screener", "Screen")
    Screen.objects.filter(county="NewHanover County").update(county="New Hanover County")


class Migration(migrations.Migration):
    dependencies = [
        ("screener", "0153_add_needs_disability_resources"),
    ]

    operations = [
        # noop reverse: rolling back cannot recover which rows had the typo — data fix is irreversible
        migrations.RunPython(fix_new_hanover_county_typo, migrations.RunPython.noop),
    ]
