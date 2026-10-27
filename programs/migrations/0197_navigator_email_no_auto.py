from collections import defaultdict

from django.apps.registry import Apps
from django.conf import settings
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# Mirrors translations.models.BLANK_TRANSLATION_PLACEHOLDER: an English row that is still
# the placeholder has no address to copy.
BLANK_TRANSLATION_PLACEHOLDER = "[PLACEHOLDER]"


def forwards(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Make every navigator email the English address in every language (MFB-2292).

    Navigator emails were created auto-translatable, so machine translation rewrote them:
    `información@…`, `coordinador@…`, `info@wa211.org मा जानुहोस्।`. In production 175 rows
    across 89 navigators differed from English, and 70 of those still looked like valid
    addresses. Marking the parents no_auto makes a later English edit (admin or config
    import) copy to every language instead of translating it.

    Each non-English row is overwritten with the English text and `edited=False`, the state
    a no_auto copy leaves it in. `edited=True` would make `edit_translation_by_id` refuse the
    next non-manual copy for that row. All production rows were `edited=False` already.
    A navigator whose English email is blank or the placeholder has nothing to copy and is
    only marked no_auto. Re-running changes nothing.
    """
    Translation = apps.get_model("translations", "Translation")
    TranslationTranslation = apps.get_model("translations", "TranslationTranslation")

    email_ids = set(Translation.objects.filter(navigator_email__isnull=False).values_list("id", flat=True))
    marked = Translation.objects.filter(id__in=email_ids, no_auto=False).update(no_auto=True)

    rows_by_email: dict[int, dict[str, object]] = defaultdict(dict)
    for row in TranslationTranslation.objects.filter(master_id__in=email_ids):
        rows_by_email[row.master_id][row.language_code] = row

    changed = []
    for rows in rows_by_email.values():
        english = rows.get(settings.LANGUAGE_CODE)
        if english is None or (english.text or "").strip() in ("", BLANK_TRANSLATION_PLACEHOLDER):
            continue
        for language_code, row in rows.items():
            if language_code == settings.LANGUAGE_CODE:
                continue
            if row.text != english.text or row.edited:
                row.text = english.text
                row.edited = False
                changed.append(row)

    TranslationTranslation.objects.bulk_update(changed, ["text", "edited"], batch_size=500)

    if changed or marked:
        # The results page reads translations through a cache that would otherwise serve
        # the old text for up to a day. Live code: the cache keys aren't part of any model.
        from translations.models import _invalidate_translation_cache

        _invalidate_translation_cache()

    print(f"  marked {marked} navigator emails no_auto; copied English onto {len(changed)} translated rows")


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0196_move_state_ssi_current_benefits"),
        ("translations", "0006_move_zh_data"),
    ]

    operations = [
        # No reverse: the overwritten text was machine output pointing at the wrong inboxes.
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
