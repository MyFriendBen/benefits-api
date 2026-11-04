from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0201_move_state_wic_current_benefits"),
    ]
    operations = [
        migrations.AlterField(
            model_name="program",
            name="year_type",
            field=models.CharField(
                choices=[
                    ("hardcoded", "Hardcoded"),
                    ("fiscal_year", "Fiscal Year"),
                    ("calendar_year", "Calendar Year"),
                    ("prior_tax_year", "Prior Tax Year"),
                ],
                default="hardcoded",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="program",
            name="flip_month",
            field=models.IntegerField(
                default=1,
                help_text="Month (1-12) when roll_program_years moves this program to the next period. 1=Jan, 2=Feb, 10=Oct.",
            ),
        ),
        migrations.AddField(
            model_name="program",
            name="year_offset",
            field=models.IntegerField(
                default=0,
                help_text="Offset applied to the target year. -1 for prior tax year (e.g. 2026 target -> 2025 period).",
            ),
        ),
    ]
