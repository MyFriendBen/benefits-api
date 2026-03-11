from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0146_merge_20260224_0000"),
    ]

    operations = [
        migrations.AddField(
            model_name="screen",
            name="has_ccad",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
