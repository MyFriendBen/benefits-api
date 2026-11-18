"""
Navigator languages use the site's locale codes, so Chinese moves from `zh` to `zh-hans`. The
program page shows nothing that tells the two apart, and the site renamed its own `zh` to
`zh-hans` earlier (translations/migrations/0006_move_zh_data.py).

Every navigator listing `zh` moves to `zh-hans`, and the badge's translation moves from
`navLanguage.zh` to `navLanguage.zh-hans` with all its languages' text.
"""

from django.db import migrations

OLD, NEW = "zh", "zh-hans"
OLD_BADGE, NEW_BADGE = f"navLanguage.{OLD}", f"navLanguage.{NEW}"


def move_to_zh_hans(apps, schema_editor) -> None:
    NavigatorLanguage = apps.get_model("programs", "NavigatorLanguage")
    Navigator = apps.get_model("programs", "Navigator")
    Translation = apps.get_model("translations", "Translation")

    old = NavigatorLanguage.objects.filter(code=OLD).first()
    if old is not None:
        if NavigatorLanguage.objects.filter(code=NEW).exists():
            new = NavigatorLanguage.objects.get(code=NEW)
            for navigator in Navigator.objects.filter(languages=old):
                navigator.languages.add(new)
                navigator.languages.remove(old)
            old.delete()
        else:
            NavigatorLanguage.objects.filter(pk=old.pk).update(code=NEW)

    if not Translation.objects.filter(label=NEW_BADGE).exists():
        Translation.objects.filter(label=OLD_BADGE).update(label=NEW_BADGE)

    # A bulk update skips the model's own cache invalidation.
    from translations.models import _invalidate_translation_cache

    _invalidate_translation_cache()


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0213_remove_unknown_legal_statuses"),
        ("translations", "0006_move_zh_data"),
    ]

    # `zh` is no longer a navigator language, so reversing leaves `zh-hans` in place.
    operations = [migrations.RunPython(move_to_zh_hans, migrations.RunPython.noop)]
