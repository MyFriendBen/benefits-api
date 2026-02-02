from configuration.models import Configuration
from rest_framework import serializers
from .fields import OrderedJSONField


class ConfigurationSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    data = OrderedJSONField()
    feature_flags = serializers.SerializerMethodField()

    class Meta:
        model = Configuration
        fields = "__all__"

    def get_feature_flags(self, obj):
        """Return feature flags from the related WhiteLabel."""
        return obj.white_label.feature_flags if obj.white_label else {}
