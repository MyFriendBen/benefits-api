from django.db import migrations


def rename_cesn_andso_care(apps, schema_editor):
    """
    The cesn WL had Program records named co_andso and co_care — keys that belong to the
    CO WL. Rename them to cesn_andso and cesn_care to follow the cesn_* convention and
    free up co_andso/co_care for new CO WL tracking programs in the next migration.

    Translation labels are keyed by program ID (e.g. program.co_andso_1257-name) so they
    do not need to change.
    """
    Program = apps.get_model("programs", "Program")

    Program.objects.filter(
        white_label__code="cesn",
        name_abbreviated="co_andso",
    ).update(name_abbreviated="cesn_andso")

    Program.objects.filter(
        white_label__code="cesn",
        name_abbreviated="co_care",
    ).update(name_abbreviated="cesn_care")


def reverse_rename_cesn_andso_care(apps, schema_editor):
    Program = apps.get_model("programs", "Program")

    Program.objects.filter(
        white_label__code="cesn",
        name_abbreviated="cesn_andso",
    ).update(name_abbreviated="co_andso")

    Program.objects.filter(
        white_label__code="cesn",
        name_abbreviated="cesn_care",
    ).update(name_abbreviated="co_care")


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0139_delete_cocb_program"),
    ]

    operations = [
        migrations.RunPython(rename_cesn_andso_care, reverse_rename_cesn_andso_care),
    ]
