from django.contrib import admin
from django.urls import reverse
from authentication.admin import SecureAdmin
from .models import WhiteLabel


class WhiteLabelAdmin(SecureAdmin):
    search_fields = ("name",)
    list_display = ("name", "code", "state_code")
    list_filter = ("state_code",)
    exclude = ("feature_flags",)


# Proxy model for separate Feature Flags admin section
class FeatureFlags(WhiteLabel):
    class Meta:
        proxy = True
        verbose_name = "Feature Flag"
        verbose_name_plural = "Feature Flags"


class FeatureFlagsAdmin(SecureAdmin):
    list_display = ("name", "code", "get_feature_flags_summary")
    list_filter = ("state_code",)
    search_fields = ("name", "code")
    readonly_fields = ("name",)
    fields = ("name",)
    change_form_template = "admin/screener/featureflags/change_form.html"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)

        # Build feature flags context for template
        flags_for_template = []
        feature_flags = obj.feature_flags or {}
        for flag_key, flag_config in WhiteLabel.FEATURE_FLAGS.items():
            flags_for_template.append({
                "key": flag_key,
                "label": flag_config.label,
                "description": flag_config.description,
                "scope": flag_config.scope,
                "enabled": feature_flags.get(flag_key, flag_config.default),
            })

        extra_context = extra_context or {}
        extra_context["feature_flags"] = flags_for_template
        extra_context["whitelabel_admin_url"] = reverse("admin:screener_whitelabel_change", args=[object_id])
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        # Build feature_flags dict from checkboxes in POST data
        feature_flags = {}
        for flag_key in WhiteLabel.FEATURE_FLAGS:
            feature_flags[flag_key] = flag_key in request.POST
        obj.feature_flags = feature_flags
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return False

    def get_feature_flags_summary(self, obj):
        """Show a summary of enabled features using human-readable labels."""
        if not obj.feature_flags:
            return "No features configured"
        enabled = []
        disabled = []
        for key, value in obj.feature_flags.items():
            flag_config = WhiteLabel.FEATURE_FLAGS.get(key)
            label = flag_config.label if flag_config else key
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

    get_feature_flags_summary.short_description = "Features"


admin.site.register(WhiteLabel, WhiteLabelAdmin)
admin.site.register(FeatureFlags, FeatureFlagsAdmin)
