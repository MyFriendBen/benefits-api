from django.contrib import admin
from django.urls import reverse
from authentication.admin import SecureAdmin
from .models import (
    AssistantConversation,
    AssistantMessage,
    BenjiSmsBinding,
    BenjiSmsDelivery,
    BenjiSmsStrangerReply,
    WhiteLabel,
)


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
    fields = (
        "seq",
        "role",
        "text",
        "rating",
        "rating_reason",
        "rated_at",
        "model",
        "prompt_tokens",
        "completion_tokens",
        "latency_ms",
        "error",
    )
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

    Superuser-only is enforced EXPLICITLY below rather than left to SecureAdmin's
    white-label scoping, which cannot work for this model and fails loudly if relied
    on. `SecureAdmin._model_has_white_label()` tests `hasattr(self.model,
    "white_label")`, and that is True even though `white_label` here is a plain
    CharField holding the white label *code*: Django gives every concrete field a
    `DeferredAttribute` class descriptor. So the base class takes its scoping branch
    and runs `filter(white_label__in=request.user.white_labels.all())`, comparing a
    varchar column against a subquery of integer primary keys — `ProgrammingError:
    operator does not exist: character varying = bigint`, a 500 on the changelist for
    every non-superuser staff member. These rows hold free-text household PII, so the
    correct behavior is to be invisible to tenant staff, and that is now stated as
    code instead of inferred from a base-class side effect.
    """

    always_can_view = False
    inlines = (AssistantMessageInline,)
    list_display = ("conversation_id", "screen_uuid", "white_label", "channel", "status", "mode", "updated_at")
    list_filter = ("white_label", "channel", "status", "mode")
    search_fields = ("conversation_id", "screen_uuid")
    ordering = ("-updated_at",)
    readonly_fields = (
        "conversation_id",
        "screen_uuid",
        "white_label",
        "locale",
        "mode",
        "prompt_version",
        "channel",
        "status",
        "context",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        """Superusers only. Never fall through to SecureAdmin's white-label filter.

        That filter would compare this model's `white_label` CharField against a
        queryset of WhiteLabel primary keys and raise a database type error (see the
        class docstring). Returning an empty queryset is also what we actually want
        for non-superusers, so this both fixes the 500 and makes the intent explicit.
        """
        if not self._is_superuser(request):
            return self.model._default_manager.none()
        # SecureAdmin's superuser branch returns the queryset unfiltered, so this is
        # the ordinary path once the non-superuser case is handled above.
        return super().get_queryset(request)

    def has_module_permission(self, request):
        # Keep the section out of the admin nav for tenant staff entirely — the base
        # class would show it, because _model_has_white_label() is True here.
        return self._is_superuser(request)

    def has_view_permission(self, request, obj=None):
        return self._is_superuser(request)

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


class SuperuserReadOnlyAdmin(SecureAdmin):
    """Read-only and superuser-only, stated outright rather than inherited.

    For tables tenant staff must not see at all. SecureAdmin's white-label scoping is
    the wrong tool for them: it would show `BenjiSmsBinding` (which has a real
    `white_label` FK) to that white label's staff, and for models without one it falls
    back to `always_can_view`. Every permission is answered here instead.
    """

    always_can_view = False

    def get_queryset(self, request):
        if not self._is_superuser(request):
            return self.model._default_manager.none()
        return super().get_queryset(request)

    def has_module_permission(self, request):
        return self._is_superuser(request)

    def has_view_permission(self, request, obj=None):
        return self._is_superuser(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Benji SMS (MFB-2435). benefits-api's SMS code is the only writer of these tables, and
# a hand-edit would desynchronize routing and consent from what was actually texted.
#
# The phone hash is shown only as an opaque value for support lookups, and search is
# by hash only. Searching by phone number would be convenient, but it would put the
# number in the admin URL's query string, and so in server logs and browser history.


class BenjiSmsBindingAdmin(SuperuserReadOnlyAdmin):
    list_display = ("id", "screen_uuid", "white_label", "status", "revoked_at", "shared_until", "created_at")
    list_filter = ("status", "white_label")
    # The uuids are searched as text, as on AssistantConversationAdmin: an exact lookup
    # would raise on any query that is not a valid uuid, a hash included.
    search_fields = ("=phone_hash", "screen_uuid", "conversation__conversation_id")
    ordering = ("-created_at",)
    readonly_fields = (
        "phone_hash",
        "screen_uuid",
        "white_label",
        "conversation",
        "status",
        "consented_at",
        "consent_version",
        "revoked_at",
        "shared_until",
        "created_at",
        "last_inbound_at",
    )
    list_select_related = ("white_label",)


class BenjiSmsDeliveryAdmin(SuperuserReadOnlyAdmin):
    list_display = ("id", "kind", "delivery_status", "delivery_error_code", "segments", "sent_at", "status_at")
    list_filter = ("kind", "delivery_status")
    search_fields = ("=inbound_sid", "=outbound_sid")
    ordering = ("-created_at",)
    readonly_fields = (
        "kind",
        "message",
        "binding",
        "inbound_sid",
        "outbound_sid",
        "delivery_status",
        "delivery_error_code",
        "segments",
        "remainder_text",
        "created_at",
        "sent_at",
        "status_at",
    )


class BenjiSmsStrangerReplyAdmin(SuperuserReadOnlyAdmin):
    list_display = ("id", "replied_at")
    search_fields = ("=phone_hash",)
    ordering = ("-replied_at",)
    readonly_fields = ("phone_hash", "replied_at")


admin.site.register(BenjiSmsBinding, BenjiSmsBindingAdmin)
admin.site.register(BenjiSmsDelivery, BenjiSmsDeliveryAdmin)
admin.site.register(BenjiSmsStrangerReply, BenjiSmsStrangerReplyAdmin)
