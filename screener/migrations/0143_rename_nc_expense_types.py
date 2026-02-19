from django.db import migrations


def rename_nc_expense_types(apps, schema_editor):
    Expense = apps.get_model("screener", "Expense")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    try:
        nc = WhiteLabel.objects.get(code="nc")
    except WhiteLabel.DoesNotExist:
        return
    nc_expenses = Expense.objects.filter(screen__white_label=nc)
    nc_expenses.filter(type="propertyTaxes").update(type="propertyTax")
    nc_expenses.filter(type="associationFees").update(type="hoa")


def reverse_rename_nc_expense_types(apps, schema_editor):
    Expense = apps.get_model("screener", "Expense")
    WhiteLabel = apps.get_model("screener", "WhiteLabel")
    try:
        nc = WhiteLabel.objects.get(code="nc")
    except WhiteLabel.DoesNotExist:
        return
    nc_expenses = Expense.objects.filter(screen__white_label=nc)
    nc_expenses.filter(type="propertyTax").update(type="propertyTaxes")
    nc_expenses.filter(type="hoa").update(type="associationFees")


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0142_merge_20260217_1810"),
    ]

    operations = [
        migrations.RunPython(rename_nc_expense_types, reverse_rename_nc_expense_types),
    ]
