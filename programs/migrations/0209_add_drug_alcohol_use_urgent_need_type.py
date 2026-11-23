# MFB-2363: adds the shared "Help with drug or alcohol use" urgent need type.
#
# Since 0207 (MFB-1867) every UrgentNeedType is a shared row (white_label = NULL)
# used by urgent needs in every white label, so this one is created shared too. Only
# NC offers the matching immediate-needs option today, but the type itself isn't
# state-specific. Following 0207's convention, external_name has no state prefix
# and the English name is machine-translated here, with an outage-safe fallback.
#
# The icon name "drug_alcohol_use" matches the key in the frontend's ICON_NAME_MAP
# (benefits-calculator/src/Components/Results/helpers.ts).

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

from integrations.clients.google_translate import Translate, is_auto_translatable

if TYPE_CHECKING:
    from programs.models import UrgentNeedType

EXTERNAL_NAME = "drug_alcohol_use"
ICON_NAME = "drug_alcohol_use"
DISPLAY_NAME = "Help with drug or alcohol use"


def forward(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    # Real models rather than apps.get_model: new_urgent_need_type and
    # add_translation need parler internals unavailable on historical models.
    from programs.models import CategoryIconName, UrgentNeedType

    if UrgentNeedType.objects.filter(external_name=EXTERNAL_NAME).exists():
        return

    if not CategoryIconName.objects.filter(name=ICON_NAME).exists():
        CategoryIconName.objects.create(name=ICON_NAME)

    urgent_need_type = UrgentNeedType.objects.new_urgent_need_type(None, EXTERNAL_NAME, ICON_NAME)
    _set_name(urgent_need_type, DISPLAY_NAME)


def _set_name(urgent_need_type: "UrgentNeedType", text: str) -> None:
    """Set the English name and machine-translate the rest (same approach as 0207)."""
    from translations.models import Translation

    translation = Translation.objects.add_translation(label=urgent_need_type.name.label, default_message=text)

    if not is_auto_translatable(text):
        return

    try:
        translated = Translate().bulk_translate(Translate.languages, [text], strict=False).get(text, {})
    except Exception:
        # A translation outage must not fail the migration; English is already
        # saved and the rest can be filled in from the admin.
        return

    for lang, translated_text in translated.items():
        if lang == settings.LANGUAGE_CODE:
            continue
        Translation.objects.edit_translation_by_id(translation.id, lang, translated_text, manual=False)


def backward(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Delete the type and its name Translation if nothing else references it."""
    from django.db import transaction
    from django.db.models import ProtectedError

    from programs.models import UrgentNeedType
    from translations.models import Translation

    urgent_need_type = UrgentNeedType.objects.filter(external_name=EXTERNAL_NAME).first()
    if urgent_need_type is None:
        return

    translation_id = urgent_need_type.name_id
    urgent_need_type.delete()

    try:
        with transaction.atomic():
            Translation.objects.filter(id=translation_id).delete()
    except ProtectedError:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0208_add_211nj_referrer"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
