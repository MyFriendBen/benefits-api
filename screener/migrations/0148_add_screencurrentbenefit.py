from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0134_program_show_in_has_benefits_step"),
        ("screener", "0147_backfill_income_category_gap"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScreenCurrentBenefit",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "screen",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="current_benefits",
                        to="screener.screen",
                    ),
                ),
                (
                    "program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="programs.program",
                    ),
                ),
            ],
            options={
                "db_table": "screener_screen_current_benefits",
            },
        ),
        migrations.AlterUniqueTogether(
            name="screencurrentbenefit",
            unique_together={("screen", "program")},
        ),
    ]
