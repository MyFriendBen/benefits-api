from django.contrib import admin
from django import forms
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


class WhiteLabelFeaturesForm(forms.ModelForm):
    class Meta:
        model = WhiteLabelFeatures
        fields = ("features",)
        widgets = {
            "features": forms.Textarea(attrs={"rows": 15, "cols": 80}),
        }
        help_texts = {
            "features": 'JSON object for feature flags. Example: {"show_eligible_member_tags": true, "show_nps_survey": false}',
        }


class WhiteLabelFeaturesAdmin(SecureAdmin):
    form = WhiteLabelFeaturesForm
    list_display = ("name", "code", "get_features_summary")
    list_filter = ("state_code",)
    search_fields = ("name", "code")
    readonly_fields = ("name", "code", "state_code")
    fieldsets = (
        ("White Label", {"fields": ("name", "code", "state_code"), "description": "Read-only white label information."}),
        ("Feature Flags", {"fields": ("features",), "description": "Configure feature flags for this white label."}),
    )

    def get_features_summary(self, obj):
        """Show a summary of enabled features."""
        if not obj.features:
            return "No features configured"
        enabled = [k for k, v in obj.features.items() if v is True]
        disabled = [k for k, v in obj.features.items() if v is False]
        parts = []
        if enabled:
            parts.append(f"✓ {', '.join(enabled)}")
        if disabled:
            parts.append(f"✗ {', '.join(disabled)}")
        return " | ".join(parts) if parts else "No features configured"

    get_features_summary.short_description = "Features"


admin.site.register(WhiteLabel, WhiteLabelAdmin)
admin.site.register(WhiteLabelFeatures, WhiteLabelFeaturesAdmin)
