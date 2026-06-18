from django.db import migrations
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist


def forwards_func(apps, schema_editor) -> None:
    Program = apps.get_model("programs", "Program")
    ProgramTranslation = apps.get_model("programs", "ProgramTranslation")

    for object in Program.objects.all():
        ProgramTranslation.objects.create(
            master_id=object.pk,
            language_code=settings.LANGUAGE_CODE,
            description_short=object._description_short,
            name=object._name,
            name_abbreviated=object._name_abbreviated,
            description=object._description,
            learn_more_link=object._learn_more_link,
            apply_button_link=object._apply_button_link,
            dollar_value=object._dollar_value,
            value_type=object._value_type,
            estimated_delivery_time=object._estimated_delivery_time,
            legal_status_required=object._legal_status_required,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("programs", "0011_add_translation_model"),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
