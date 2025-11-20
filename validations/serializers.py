from django.db.models import ObjectDoesNotExist
from rest_framework import serializers
from screener.models import Screen
from validations.models import Validation


class ValidationSerializer(serializers.ModelSerializer):
    screen_uuid = serializers.UUIDField()

    class Meta:
        model = Validation
        fields = (
            "id",
            "screen_uuid",
            "program_name",
            "eligible",
            "value",
            "notes",
            "created_date",
        )
        read_only_field = ("created_date", "id")

    def validate(self, attrs):
        screen_uuid = attrs.pop("screen_uuid")
        try:
            screen = Screen.objects.get(uuid=screen_uuid)
        except ObjectDoesNotExist:
            raise serializers.ValidationError("screen with that uuid does not exist")

        if not screen.is_test_data:
            raise serializers.ValidationError("screen is not a test")

        attrs["screen"] = screen

        return attrs
