from django import template
from django.conf import settings

register = template.Library()


@register.filter
def get_datetime_label(history_date, lang_code=None, default="Never"):
    if not history_date:
        return default

    date = history_date.get(lang_code, default) if lang_code else history_date
    return date.isoformat() if hasattr(date, "isoformat") else (date or default)


@register.filter
def get_update_type(translation, lang_code):
    for record in translation.translations.all():
        if record.language_code == lang_code:
            return record.edited


@register.filter
def get_language_name(lang_code):
    return dict(settings.LANGUAGES).get(lang_code, lang_code)
