from configuration.models import Configuration
from rest_framework import serializers
from screener.models import WhiteLabel
from .fields import OrderedJSONField


class ConfigurationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    data = OrderedJSONField()
    feature_flags = serializers.SerializerMethodField()

    class Meta:
        model = Configuration
        fields = "__all__"

    def get_feature_flags(self, obj) -> dict[str, bool]:
        """Return frontend-scoped feature flags from the related WhiteLabel."""
        if not obj.white_label:
            return {}

        return {
            key: obj.white_label.get_flag_value(key)
            for key, config in WhiteLabel.FEATURE_FLAGS.items()
            if config.scope in ("frontend", "both")
        }
