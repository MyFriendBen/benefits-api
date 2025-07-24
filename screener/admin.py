from django.contrib import admin
from authentication.admin import SecureAdmin
from .models import WhiteLabel


class WhiteLabelAdmin(SecureAdmin):
    search_fields = ("name",)


admin.site.register(WhiteLabel, WhiteLabelAdmin)
