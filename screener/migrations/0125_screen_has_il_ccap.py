# Generated manually for IL CCAP

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('screener', '0124_rename_needs_savings_to_needs_college_savings'),
    ]

    operations = [
        migrations.AddField(
            model_name='screen',
            name='has_il_ccap',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
