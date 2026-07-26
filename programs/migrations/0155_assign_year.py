from django.db import migrations


def assign_dynamic_fpl_rows(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    FederalPoveryLimit = apps.get_model("programs", "FederalPoveryLimit")

    calendar_fpl = FederalPoveryLimit.objects.get(year="THIS_YEAR_CALENDAR")
    fiscal_fpl = FederalPoveryLimit.objects.get(year="THIS_YEAR_FISCAL")

    Program.objects.filter(year_type="calendar_year").update(year=calendar_fpl)
    Program.objects.filter(year_type="fiscal_year").update(year=fiscal_fpl)
    # hardcoded programs are intentionally left unchanged


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0154_add_year_type_to_program"),
    ]
    operations = [
        migrations.RunPython(assign_dynamic_fpl_rows, migrations.RunPython.noop),
    ]
