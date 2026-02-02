from django.contrib import admin
from authentication.admin import SecureAdmin
from .models import WhiteLabel


class WhiteLabelAdmin(SecureAdmin):
    search_fields = ("name",)
    list_display = ("name", "code", "state_code")
    list_filter = ("state_code",)
    exclude = ("features",)


# Proxy model for separate Feature Flags admin section
class WhiteLabelFeatures(WhiteLabel):
    class Meta:
        proxy = True
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"


class WhiteLabelFeaturesAdmin(SecureAdmin):
    list_display = ("name", "code", "get_features_summary")
    list_filter = ("state_code",)
    search_fields = ("name", "code")
    readonly_fields = ("name", "code", "state_code")
    fields = ("name", "code", "state_code")
    change_form_template = "admin/screener/whitelabelfeatures/change_form.html"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)

        # Build feature flags context for template
        feature_flags = []
        for flag_key, flag_config in WhiteLabel.FEATURE_FLAGS.items():
            enabled = obj.features.get(flag_key, flag_config["default"]) if obj.features else flag_config["default"]
            feature_flags.append({
                "key": flag_key,
                "label": flag_config["label"],
                "description": flag_config["description"],
                "enabled": enabled,
            })

        extra_context = extra_context or {}
        extra_context["feature_flags"] = feature_flags
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        # Build features dict from checkboxes in POST data
        features = {}
        for flag_key in WhiteLabel.FEATURE_FLAGS:
            features[flag_key] = flag_key in request.POST
        obj.features = features
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return False

    def get_features_summary(self, obj):
        """Show a summary of enabled features using human-readable labels."""
        if not obj.features:
            return "No features configured"
        enabled = []
        disabled = []
        for key, value in obj.features.items():
            label = WhiteLabel.FEATURE_FLAGS.get(key, {}).get("label", key)
            if value:
                enabled.append(label)
            else:
                disabled.append(label)
        parts = []
        if enabled:
            parts.append(f"✓ {', '.join(enabled)}")
        if disabled:
            parts.append(f"✗ {', '.join(disabled)}")
        return " | ".join(parts) if parts else "No features configured"

    get_features_summary.short_description = "Features"


admin.site.register(WhiteLabel, WhiteLabelAdmin)
admin.site.register(WhiteLabelFeatures, WhiteLabelFeaturesAdmin)
