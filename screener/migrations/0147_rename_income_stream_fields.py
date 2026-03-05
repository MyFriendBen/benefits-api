from django.db import migrations


class Migration(migrations.Migration):
    """
    Renames IncomeStream fields to match UI terminology:
      - category -> type  (the grouping: employment, government, support, investment)
      - type     -> source (the specific income: wages, selfEmployment, sSI, etc.)

    Two-step rename to avoid the intermediate state where both fields have the same name:
      1. Rename `type` -> `source`
      2. Rename `category` -> `type`
    """

    dependencies = [
        ("screener", "0146_merge_20260224_0000"),
    ]

    operations = [
        # Step 1: rename the specific income field (type -> source)
        migrations.RenameField(
            model_name="incomestream",
            old_name="type",
            new_name="source",
        ),
        # Step 2: rename the grouping field (category -> type)
        migrations.RenameField(
            model_name="incomestream",
            old_name="category",
            new_name="type",
        ),
    ]
