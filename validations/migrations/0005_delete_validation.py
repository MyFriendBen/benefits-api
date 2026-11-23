from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("validations", "0004_validation_updated_date_and_more"),
        ("screener", "0161_screen_needs_medical_expenses_and_debt"),
    ]

    operations = [
        migrations.DeleteModel(name="Validation"),
    ]
