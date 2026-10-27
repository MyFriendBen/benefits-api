from django.db import migrations


def delete_category_benefits(apps, schema_editor):
    Configuration = apps.get_model("configuration", "Configuration")
    Configuration.objects.filter(name="category_benefits").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0006_policyengineconfig"),
    ]

    operations = [
        migrations.RunPython(delete_category_benefits, migrations.RunPython.noop),
    ]
