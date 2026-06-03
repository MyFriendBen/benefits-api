from django.contrib import admin
from django_json_widget.widgets import JSONEditorWidget
from django.db.models import JSONField
from authentication.admin import SecureAdmin
from .models import Configuration, PolicyEngineConfig
import json


class ConfigurationAdmin(SecureAdmin):
    formfield_overrides = {
        JSONField: {
            "widget": JSONEditorWidget(options={"modes": ["tree", "code"], "mode": "tree", "enableDrag": False})
        },
    }
    search_fields = ("name", "white_label__name")
    list_display = ("name", "white_label_name", "active")
    list_editable = ["active"]

    def white_label_name(self, obj):
        return obj.white_label.name

    white_label_name.admin_order_field = "white_label__name"
    white_label_name.short_description = "White Label"

    # Convert the JSON string to a dictionary
    # This makes it so that the JSON data coming from the 'data' field of the Configuration model
    # is displayed as a dictionary and without the escape characters
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and isinstance(obj.data, str):
            obj.data = json.loads(obj.data)
        return form


admin.site.register(Configuration, ConfigurationAdmin)


class PolicyEngineConfigAdmin(SecureAdmin):
    """Global singleton. SecureAdmin already restricts a white-label-less model to
    superusers; we additionally enforce single-row UX (no add once it exists, no delete).

    The change form shows a readonly "Current version" line above the editable field;
    to reset to PolicyEngine's default, clear the field and save (per its help_text)."""

    DEFAULT_LABEL = "(default — PolicyEngine current)"

    list_display = ("version_display",)
    readonly_fields = ("current_version",)
    fields = ("current_version", "policyengine_version")

    @admin.display(description="Version")
    def version_display(self, obj):
        # Make the "blank = use PolicyEngine's default" state explicit rather than an
        # empty cell.
        return obj.policyengine_version or self.DEFAULT_LABEL

    @admin.display(description="Current version")
    def current_version(self, obj):
        # Readonly echo of the active value, so the form states what is in effect (the
        # editable field below is empty when on default, which alone reads as "unset").
        # obj is None on the add form (fresh DB, no row yet) — show the default label.
        if obj is None:
            return self.DEFAULT_LABEL
        return obj.policyengine_version or self.DEFAULT_LABEL

    def has_add_permission(self, request):
        if PolicyEngineConfig.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(PolicyEngineConfig, PolicyEngineConfigAdmin)
