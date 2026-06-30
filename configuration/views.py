from django.conf import settings
from django.shortcuts import get_object_or_404
from configuration.models import Configuration
from configuration.serializers import ConfigurationSerializer
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.decorators import api_view
from programs.models import FormOption
from screener.models import WhiteLabel


def _default_message(translation) -> str:
    # Read the default-language text from the prefetched translations. Translation.default_message
    # calls .filter(), which bypasses the prefetch cache and triggers a query per option.
    return next(
        (t.text for t in translation.translations.all() if t.language_code == settings.LANGUAGE_CODE),
        "",
    )


def _serialize_form_options(white_label: WhiteLabel, option_type: str) -> list:
    options = (
        FormOption.objects.filter(white_label=white_label, option_type=option_type, active=True)
        .select_related("icon", "text")
        .prefetch_related("text__translations")
        .order_by("order", "id")
    )
    return [
        {
            "value": opt.value,
            "icon": opt.icon.lucide_name if opt.icon else None,
            "text": {
                "label": opt.text.label,
                "default_message": _default_message(opt.text),
            },
        }
        for opt in options
    ]


@api_view(["GET"])
def get_form_options(request, white_label_code: str):
    # code is not unique at the DB level, so .get() could raise MultipleObjectsReturned and 500.
    # Select deterministically by lowest id and treat "no match" as a controlled 404.
    white_label = WhiteLabel.objects.filter(code=white_label_code).order_by("id").first()
    if white_label is None:
        return Response({"error": "White label not found"}, status=404)

    # referral_options is intentionally omitted — referral sources are managed by the Referrer model.
    return Response(
        {
            "condition_options": _serialize_form_options(white_label, "condition"),
            "health_insurance_options": _serialize_form_options(white_label, "health_insurance"),
        }
    )


class ConfigurationView(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows configurations to be viewed.
    """

    serializer_class = ConfigurationSerializer
    permission_classes = [permissions.DjangoModelPermissions]

    def get_queryset(self):
        return Configuration.objects.select_related("white_label").filter(
            active=True, white_label__code=self.kwargs["white_label"]
        )

    def retrieve(self, request, pk=None):
        configuration = get_object_or_404(self.get_queryset(), name=pk)
        serializer = ConfigurationSerializer(configuration)
        return Response(serializer.data)
