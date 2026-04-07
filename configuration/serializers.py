import json
from collections import OrderedDict

from configuration.models import Configuration
from programs.models import Referrer
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
            key: obj.white_label._get_flag_value(key)
            for key, config in WhiteLabel.FEATURE_FLAGS.items()
            if config.scope in ("frontend", "both")
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if instance.name == "referral_options":
            ret["data"] = json.dumps(self._build_referral_options(instance.white_label))

        return ret

    def _build_referral_options(self, white_label: WhiteLabel) -> OrderedDict:
        """Build referral_options data from Referrer model rows.

        Returns the same shape the frontend expects: an ordered dict mapping
        referrer_code to either a plain string or a {_label, _default_message} dict.
        """
        referrers = Referrer.objects.filter(
            white_label=white_label,
            show_in_dropdown=True,
        ).order_by("pk")

        options = OrderedDict()
        for ref in referrers:
            options[ref.referrer_code] = ref.name

        return options
