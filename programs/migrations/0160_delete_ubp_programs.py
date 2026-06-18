# Colorado Utility Bill Help ended 2026-05-31. Deletes the ubp and cesn_ubp Program
# rows so they no longer appear in results or the has-benefits step.

from django.db import migrations


def delete_ubp_programs(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(white_label__code="co", name_abbreviated="ubp").delete()
    Program.objects.filter(white_label__code="cesn", name_abbreviated="cesn_ubp").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0159_seed_ks_generic_referrers"),
    ]

    operations = [
        migrations.RunPython(delete_ubp_programs, migrations.RunPython.noop),
    ]
