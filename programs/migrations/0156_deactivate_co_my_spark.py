from django.db import migrations


def deactivate_my_spark(apps, schema_editor):
    # myspark is exclusive to the Colorado white label (Denver Public Schools only)
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(name_abbreviated="myspark").update(active=False)


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0155_program_unique_wl_name_abbreviated"),
    ]
    operations = [
        # noop reverse: rolling back should not reactivate — reactivation should be handled separately
        migrations.RunPython(deactivate_my_spark, migrations.RunPython.noop),
    ]
