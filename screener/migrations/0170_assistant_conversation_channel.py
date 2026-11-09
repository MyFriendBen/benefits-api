# MFB-2432: a channel on Benji conversations, so a texted conversation and the web
# widget's can coexist on one screen (MFB-1916 proposal v2, decision 3).
#
# DEPLOY ORDER: this migration ships BEFORE the ai-service release that reads and
# writes `channel`. That only works because of the RunSQL below. Django 4.2 has no
# `db_default`: AddField sets the default for the backfill and then drops it, leaving
# a NOT NULL column with no database default. ai-service inserts with raw SQL and,
# until its own release, names no channel, so every new conversation would fail.
# Keeping DEFAULT 'web' in the database makes those inserts land as web
# conversations, which is what they are. The default stays after ai-service ships:
# it is harmless, and it keeps any other raw-SQL writer working.
#
# The new unique constraint is added BEFORE the old one is removed, so there is no
# moment in which two active conversations for one screen could be inserted. While
# both exist, the old one is the stricter of the two, and every row is 'web' anyway.
#
# Locking: adding a column with a constant default is a catalog-only change in
# Postgres 11+, with no table rewrite. Building the partial unique index and checking
# the CHECK constraint each scan the table under a lock that blocks writes. This table
# holds one row per Benji conversation, small enough that the scan is brief.

from django.db import migrations, models

# ROLLBACK: reversing this migration re-creates the old one-active-per-screen index,
# which cannot be built once a screen has an active web AND an active SMS conversation
# (the state this migration exists to allow). The reverse guard below checks for that
# first and stops with instructions, rather than failing halfway on a duplicate key.
_SCREENS_WITH_SEVERAL_ACTIVE = """
SELECT screen_uuid FROM screener_assistantconversation
WHERE status = 'active'
GROUP BY screen_uuid
HAVING COUNT(*) > 1
LIMIT 5
"""


def _refuse_rollback_while_channels_coexist(apps, schema_editor) -> None:
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(_SCREENS_WITH_SEVERAL_ACTIVE)
        screens = [str(row[0]) for row in cursor.fetchall()]
    if screens:
        raise RuntimeError(
            "Cannot reverse screener 0170: some screens have more than one active Benji "
            f"conversation (for example {', '.join(screens)}), and the one-per-screen "
            "index it would restore cannot be built over them. Set status='closed' on "
            "every active non-web conversation first, then migrate back."
        )


_SET_DB_DEFAULT = "ALTER TABLE screener_assistantconversation ALTER COLUMN channel SET DEFAULT 'web'"
_DROP_DB_DEFAULT = "ALTER TABLE screener_assistantconversation ALTER COLUMN channel DROP DEFAULT"


class Migration(migrations.Migration):

    dependencies = [
        ("screener", "0169_screen_household_size_range"),
    ]

    operations = [
        migrations.AddField(
            model_name="assistantconversation",
            name="channel",
            field=models.CharField(
                choices=[("web", "Web widget"), ("sms", "Text message")], default="web", max_length=8
            ),
        ),
        migrations.RunSQL(sql=_SET_DB_DEFAULT, reverse_sql=_DROP_DB_DEFAULT),
        migrations.AddConstraint(
            model_name="assistantconversation",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "active")),
                fields=("screen_uuid", "channel"),
                name="assistant_one_active_conv_per_screen_channel",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="assistantconversation",
            name="assistant_one_active_conv_per_screen",
        ),
        # Forward: nothing. Reverse: runs just before the old index is re-created.
        migrations.RunPython(migrations.RunPython.noop, reverse_code=_refuse_rollback_while_channels_coexist),
        migrations.AddConstraint(
            model_name="assistantconversation",
            constraint=models.CheckConstraint(
                check=models.Q(("channel__in", ["web", "sms"])), name="assistant_conv_channel_valid"
            ),
        ),
        # State only: choices are not a database concept, so this emits no SQL.
        migrations.AlterField(
            model_name="assistantconversation",
            name="status",
            field=models.CharField(
                choices=[("active", "Active"), ("closed", "Closed"), ("expired", "Expired")],
                default="active",
                max_length=16,
            ),
        ),
    ]
