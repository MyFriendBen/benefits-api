from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin
from django.core.exceptions import PermissionDenied
from rest_framework.authtoken.models import TokenProxy
from rest_framework.authtoken.admin import TokenAdmin
from unfold.admin import ModelAdmin, forms
from .models import User


class SecureAdmin(ModelAdmin):
    class Media:
        css = {"all": ("css/style.css",)}

    always_can_view = False

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if self._is_superuser(request):
            return qs

        if not self._model_has_white_label():
            return qs if self.always_can_view else qs.none()

        return qs.filter(white_label__in=request.user.white_labels.all())

    def has_obj_permission(self, request, obj):
        if self._is_superuser(request):
            return True

        if not self._model_has_white_label():
            return False

        if obj is None:
            return True

        return obj.white_label in request.user.white_labels.all()

    def has_view_permission(self, request, obj=None):
        return self.has_obj_permission(request, obj) or self.always_can_view

    def has_change_permission(self, request, obj=None):
        return self.has_obj_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_obj_permission(request, obj)

    def has_add_permission(self, request):
        if not self._model_has_white_label():
            return self._is_superuser(request)

        return True

    def has_module_permission(self, request):
        if self._is_superuser(request):
            return True

        return self._model_has_white_label() or self.always_can_view

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        for field_name in form.base_fields:
            field = form.base_fields[field_name]
            if isinstance(field, forms.ModelChoiceField):
                self._set_select_queryset(field_name, field, obj, request)

        return form

    def _set_select_queryset(self, field_name: str, field: forms.ModelMultipleChoiceField, obj, request):
        user: User = request.user

        # filter the white label field
        if field_name == "white_label":
            if self._is_superuser(request):
                return
            field.queryset = field.queryset.filter(id__in=user.white_labels.all())
            return

        # filter the selects to only the ones that the user has access to
        if hasattr(field.queryset.model, "white_label"):
            if not self._is_superuser(request):
                field.queryset = field.queryset.filter(white_label__in=user.white_labels.all())

            if obj is not None:
                field.queryset = field.queryset.filter(white_label=obj.white_label)

    # remove the history view for non super users
    def history_view(self, request, object_id, extra_context=None):
        if not self._is_superuser(request):
            raise PermissionDenied()

        return super().history_view(request, object_id, extra_context)

    # remove the history button for non super users
    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        if not self._is_superuser(request):
            context["show_history"] = False
        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)

    def _model_has_white_label(self):
        return hasattr(self.model, "white_label")

    def _is_superuser(self, request):
        return request.user.is_superuser


class CustomUserAdmin(SecureAdmin):
    search_fields = ("email",)
    ordering = ("email_or_cell", "email")
    filter_horizontal = ["white_labels", "user_permissions"]

    list_display = ("email_or_cell", "is_staff")


class CustomGroupAdmin(SecureAdmin, GroupAdmin):
    pass


class CustomTokenAdmin(SecureAdmin, TokenAdmin):
    search_fields = ("user__email_or_cell",)


admin.site.register(User, CustomUserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)
admin.site.unregister(TokenProxy)
admin.site.register(TokenProxy, CustomTokenAdmin)
