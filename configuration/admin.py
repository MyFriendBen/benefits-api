from django.contrib import admin
from django_json_widget.widgets import JSONEditorWidget
from django.db.models import JSONField
from authentication.admin import SecureAdmin
from .models import Configuration
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
