from django.db import migrations


def forward(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(
        white_label__code="wa",
        name_abbreviated="wa_head_start",
    ).update(show_in_has_benefits_step=True)


def reverse(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(
        white_label__code="wa",
        name_abbreviated="wa_head_start",
    ).update(show_in_has_benefits_step=False)


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0152_backfill_has_benefits_categories"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
