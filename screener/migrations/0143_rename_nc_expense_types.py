from django.db import migrations


def rename_nc_expense_types(apps, schema_editor):
    Expense = apps.get_model("screener", "Expense")
    Expense.objects.filter(type="propertyTaxes").update(type="propertyTax")
    Expense.objects.filter(type="associationFees").update(type="hoa")


def reverse_rename_nc_expense_types(apps, schema_editor):
    Expense = apps.get_model("screener", "Expense")
    Expense.objects.filter(type="propertyTax").update(type="propertyTaxes")
    Expense.objects.filter(type="hoa").update(type="associationFees")


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0142_merge_20260217_1810"),
    ]

    operations = [
        migrations.RunPython(rename_nc_expense_types, reverse_rename_nc_expense_types),
    ]
