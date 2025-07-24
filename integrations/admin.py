from django.contrib import admin
from authentication.admin import SecureAdmin
from integrations.models import Link


class LinkAdmin(SecureAdmin):
    search_fields = ("link",)
    list_display = ["validated", "valid_status_code", "status_code", "in_use", "link"]


admin.site.register(Link, LinkAdmin)
