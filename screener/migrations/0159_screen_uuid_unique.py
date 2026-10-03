import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Record the unique index on Screen.uuid.

    Every screener request looks a screen up by uuid, and the column had no index:
    Postgres sequentially scanned all ~222k rows on each one (~70ms, growing with the
    table). The index was created on production directly, concurrently, so this
    migration only brings Django's model state in line with the database.

    Environments built from migrations still need the index, so the operation is
    wrapped in SeparateDatabaseAndState: the state_operations half updates the model,
    and the database_operations half creates the index only where it does not already
    exist.
    """

    dependencies = [
        ("screener", "0158_drop_snapshot_value_type"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="screen",
                    name="uuid",
                    field=models.UUIDField(default=uuid.uuid4, unique=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE UNIQUE INDEX IF NOT EXISTS screener_screen_uuid_uniq "
                        "ON screener_screen (uuid);"
                    ),
                    reverse_sql="DROP INDEX IF EXISTS screener_screen_uuid_uniq;",
                ),
            ],
        ),
    ]
