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
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

# ROLLBACK, part 1: no active non-web conversation may exist. Reversing re-creates the
# old one-active-per-screen index, which cannot be built while a screen has an active
# web AND an active SMS conversation. And an active SMS conversation on a screen with no
# web one would be worse than a failed index: the pre-channel ai-service would resume
# it as the widget's conversation, showing the texts in the browser. The guard checks
# first and stops with instructions, rather than failing halfway or doing that.
_ACTIVE_NON_WEB = """
SELECT conversation_id FROM screener_assistantconversation
WHERE status = 'active' AND channel <> 'web'
LIMIT 5
"""


def _refuse_rollback_while_non_web_is_active(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(_ACTIVE_NON_WEB)
        conversations = [str(row[0]) for row in cursor.fetchall()]
    if conversations:
        raise RuntimeError(
            "Cannot reverse screener 0170: there are active non-web Benji conversations "
            f"(for example {', '.join(conversations)}). The one-per-screen index it would "
            "restore cannot hold them, and the previous ai-service would show them in the "
            "widget. Set status='closed' on every active non-web conversation first, then "
            "migrate back."
        )


# ROLLBACK, part 2: keep what each conversation was. Reversing drops the `channel`
# column, and re-applying would backfill every row with the default, relabelling every
# texted conversation as a web one. So the reverse first copies a non-web channel into
# the row's `context` under this key, and the forward step restores it and removes the
# key. ai-service's context reader ignores keys it doesn't know, and by part 1 every
# row carrying the key is closed, so no prompt is ever built from it.
_STASH_KEY = "_channel_before_0170_rollback"
_STASH_CHANNEL = f"""
UPDATE screener_assistantconversation
SET context = context || jsonb_build_object('{_STASH_KEY}', channel)
WHERE channel <> 'web'
"""
_RESTORE_CHANNEL = f"""
UPDATE screener_assistantconversation
SET channel = context ->> '{_STASH_KEY}', context = context - '{_STASH_KEY}'
WHERE context ? '{_STASH_KEY}'
"""


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
        # Forward: restores channels a rollback stashed (a no-op the first time).
        # Reverse: stashes them, just before the column is dropped.
        migrations.RunSQL(sql=_RESTORE_CHANNEL, reverse_sql=_STASH_CHANNEL),
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
        migrations.RunPython(migrations.RunPython.noop, reverse_code=_refuse_rollback_while_non_web_is_active),
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
