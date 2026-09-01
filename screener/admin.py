from django.contrib import admin
from django.urls import reverse
from authentication.admin import SecureAdmin
from .models import AssistantConversation, AssistantMessage, WhiteLabel


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
    list_display = ("name", "get_feature_flags_summary")
    list_display_links = ("name",)
    list_filter = ("state_code",)
    search_fields = ("name", "code")
    readonly_fields = ("name",)
    fields = ("name",)
    change_form_template = "admin/screener/featureflags/change_form.html"

    def _user_can_access(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not getattr(request.user, "is_staff", False):
            return False
        if obj is None:
            return request.user.white_labels.exists()
        return request.user.white_labels.filter(pk=obj.pk).exists()

    def has_module_permission(self, request):
        return self._user_can_access(request)

    def has_view_permission(self, request, obj=None):
        return self._user_can_access(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._user_can_access(request, obj)

    def changelist_view(self, request, extra_context=None):
        # Disable checkboxes by removing bulk actions
        self.actions = None
        return super().changelist_view(request, extra_context)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = self.model.objects.only("name", "code", "state_code", "feature_flags")
        if request.user.is_superuser:
            return qs
        return qs.filter(pk__in=request.user.white_labels.all())

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)

        # Handle None return when object ID is invalid
        if obj is None:
            return super().change_view(request, object_id, form_url, extra_context)

        # Build feature flags context for template
        flags_for_template = [
            {
                "key": flag_key,
                "label": flag_config.label,
                "description": flag_config.description,
                "scope": flag_config.scope,
                "enabled": obj.has_feature(flag_key),
            }
            for flag_key, flag_config in WhiteLabel.FEATURE_FLAGS.items()
        ]

        extra_context = extra_context or {}
        extra_context["feature_flags"] = flags_for_template
        extra_context["whitelabel_admin_url"] = reverse("admin:screener_whitelabel_change", args=[object_id])
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        # Build feature_flags dict from checkboxes in POST data
        # Preserve existing flags to handle race condition if new flags are added during deploy
        feature_flags = obj.feature_flags.copy() if obj.feature_flags else {}
        for flag_key in WhiteLabel.FEATURE_FLAGS:
            feature_flags[flag_key] = flag_key in request.POST
        obj.feature_flags = feature_flags
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return False

    def get_feature_flags_summary(self, obj):
        """Show only enabled features."""
        enabled = [c.label for k, c in WhiteLabel.FEATURE_FLAGS.items() if obj.has_feature(k)]
        return ", ".join(enabled) if enabled else "—"

    get_feature_flags_summary.short_description = "Enabled Features"


admin.site.register(WhiteLabel, WhiteLabelAdmin)
admin.site.register(FeatureFlags, FeatureFlagsAdmin)


class AssistantMessageInline(admin.TabularInline):
    """Transcript, in `seq` order, on the conversation page."""

    model = AssistantMessage
    extra = 0
    can_delete = False
    ordering = ("seq",)
    fields = ("seq", "role", "text", "model", "prompt_tokens", "completion_tokens", "latency_ms", "error")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class AssistantConversationAdmin(SecureAdmin):
    """Read-only view of Benji transcripts. Superusers only.

    Deliberately read-only in every direction. mfb-ai-service is the writer for these
    tables (see screener/models.AssistantConversation) and reconciles nothing with the
    admin, so a hand-edit here would silently diverge from what the assistant's own
    prompt is built from — and editing a transcript after the fact is not a thing we
    should be able to do at all.

    Access falls out of SecureAdmin: `white_label` here is a CharField holding the
    white label *code*, not a ForeignKey, so `_model_has_white_label()` is False and
    non-superusers get an empty queryset. That is the intent rather than an accident
    — these rows hold free-text household PII, so they should not be visible to
    tenant staff by default.
    """

    always_can_view = False
    inlines = (AssistantMessageInline,)
    list_display = ("conversation_id", "screen_uuid", "white_label", "status", "mode", "updated_at")
    list_filter = ("white_label", "status", "mode")
    search_fields = ("conversation_id", "screen_uuid")
    ordering = ("-updated_at",)
    readonly_fields = (
        "conversation_id",
        "screen_uuid",
        "white_label",
        "locale",
        "mode",
        "prompt_version",
        "status",
        "context",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # History is retained indefinitely and deliberately (see screener/models.py),
        # so there is no routine reason to delete from here — and a click that quietly
        # destroys a household's transcript should not be one keystroke away.
        return False


admin.site.register(AssistantConversation, AssistantConversationAdmin)
