from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0138_add_features_to_whitelabel"),
    ]

    operations = [
        migrations.RenameField(
            model_name="whitelabel",
            old_name="features",
            new_name="feature_flags",
        ),
    ]
