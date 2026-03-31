from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0133_merge_0131_add_program_config_import_0132_rename_cesn"),
    ]

    operations = [
        migrations.AddField(
            model_name="program",
            name="show_in_has_benefits_step",
            field=models.BooleanField(
                default=False, help_text="Show this program in the 'already has benefits' screener step"
            ),
        ),
    ]
