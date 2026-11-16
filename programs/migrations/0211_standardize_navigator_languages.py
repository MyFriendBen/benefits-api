"""
Move navigator languages onto the codes the screener shows. From here on, saving checks every code
against `NavigatorLanguageCode`.

The program page shows a label only for codes in `NavigatorLanguageCode`, so navigators listing
`en`, `English`, `spanish` and the like showed no language. Each is moved to the code it meant,
without linking a navigator to the same language twice. Rows for codes no navigator uses are
deleted. A code that is unknown and still in use stops the migration with the navigators it's on,
rather than being guessed at.
"""

from django.db import migrations

KNOWN = {
    "en-us", "es", "vi", "fr", "am", "so", "ru", "ne", "my", "zh", "ar", "sw", "pl", "tl", "ko", "ur", "pt-br", "ht",
    "ALL",
}
REPLACEMENTS = {"en": "en-us", "english": "en-us", "English": "en-us", "spanish": "es", "Spanish": "es"}


def standardize(apps, schema_editor):
    NavigatorLanguage = apps.get_model("programs", "NavigatorLanguage")
    Navigator = apps.get_model("programs", "Navigator")

    for language in NavigatorLanguage.objects.exclude(code__in=KNOWN):
        navigators = list(Navigator.objects.filter(languages=language))
        replacement = REPLACEMENTS.get(language.code)
        if navigators and replacement is None:
            names = ", ".join(sorted(str(navigator.external_name) for navigator in navigators))
            raise RuntimeError(
                f"Navigator language '{language.code}' isn't known and is used by: {names}. Add it to the "
                f"screener and NavigatorLanguageCode, or add its replacement here."
            )
        if navigators:
            target, _ = NavigatorLanguage.objects.get_or_create(code=replacement)
            for navigator in navigators:
                navigator.languages.add(target)
                navigator.languages.remove(language)
        language.delete()


class Migration(migrations.Migration):
    dependencies = [("programs", "0210_add_drug_alcohol_use_category")]

    # The old codes were wrong, so reversing leaves the corrected ones in place.
    operations = [migrations.RunPython(standardize, migrations.RunPython.noop)]
