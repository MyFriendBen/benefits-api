from django.apps.registry import Apps
from django.db import migrations, models
import django.db.models.deletion
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def add_decision_time_translations(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """
    Give every existing program an empty decision time.

    Empty rather than the placeholder new programs used to get: empty means the wait varies, and
    a program-ops record that has researched a decision time sets it on the next import.
    """
    Program = apps.get_model("programs", "Program")
    Translation = apps.get_model("translations", "Translation")

    for program in Program.objects.all().only("id", "name_abbreviated"):
        translation = Translation.objects.add_translation(
            f"program.{program.name_abbreviated}_{program.id}-estimated_decision_time", ""
        )
        Program.objects.filter(pk=program.id).update(estimated_decision_time=translation.id)


class Migration(migrations.Migration):

    dependencies = [
        ("translations", "0006_move_zh_data"),
        ("programs", "0197_navigator_email_no_auto"),
    ]

    operations = [
        migrations.AddField(
            model_name="program",
            name="estimated_decision_time",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="program_estimated_decision_time",
                to="translations.translation",
            ),
        ),
        migrations.RunPython(add_decision_time_translations, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="program",
            name="estimated_decision_time",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="program_estimated_decision_time",
                to="translations.translation",
            ),
        ),
        migrations.AddField(
            model_name="programconfigimport",
            name="applied_record",
            field=models.JSONField(
                blank=True,
                help_text="What a program-ops record set when it was last applied, field by field. Comparing it "
                "with the record and the database tells a record edit from an admin edit.",
                null=True,
            ),
        ),
    ]
