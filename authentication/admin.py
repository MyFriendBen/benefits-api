from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin, UserAdmin
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


# UserAdmin supplies the password-hashing forms (UserCreationForm/UserChangeForm) and
# renders the stored hash as a read-only field with a link to the change-password view.
# Without it the password renders as a plain editable CharField and whatever is submitted
# is saved unhashed, locking the account out.
class CustomUserAdmin(SecureAdmin, UserAdmin):
    search_fields = ("email_or_cell", "email", "first_name", "last_name")
    ordering = ("email_or_cell",)
    filter_horizontal = ["white_labels", "user_permissions"]

    list_display = ("email_or_cell", "is_staff")

    # UserAdmin's default fieldsets reference the "username" field, which this model
    # replaces with email_or_cell, so they are declared explicitly.
    fieldsets = (
        (None, {"fields": ("email_or_cell", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "cell", "language_code")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "white_labels",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Contact preferences", {"fields": ("tcpa_consent", "explicit_tcpa_consent", "send_offers", "send_updates")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email_or_cell", "password1", "password2")}),)


class CustomGroupAdmin(SecureAdmin, GroupAdmin):
    pass


class CustomTokenAdmin(SecureAdmin, TokenAdmin):
    search_fields = ("user__email_or_cell",)


admin.site.register(User, CustomUserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)
admin.site.unregister(TokenProxy)
admin.site.register(TokenProxy, CustomTokenAdmin)
