import uuid
from typing import Optional

from django.contrib import admin
from django.db.models import Model, Q, QuerySet
from django.http import HttpRequest
from django.urls import reverse
from authentication.admin import SecureAdmin
from .models import (
    AssistantConversation,
    AssistantMessage,
    BenjiSmsBinding,
    BenjiSmsDelivery,
    BenjiSmsPhone,
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


class SuperuserReadOnlyAdmin(SecureAdmin):
    """Read-only and superuser-only, stated outright rather than inherited.

    For tables tenant staff must not see at all: Benji transcripts and the SMS tables.
    Every permission is answered here, because SecureAdmin's white-label scoping is
    the wrong tool for them in two different ways:

    - For `AssistantConversation` it fails loudly. `SecureAdmin._model_has_white_label()`
      tests `hasattr(self.model, "white_label")`, which is True even though that
      `white_label` is a plain CharField holding the white label *code*: Django gives
      every concrete field a `DeferredAttribute` class descriptor. So the base class
      runs `filter(white_label__in=request.user.white_labels.all())`, comparing a
      varchar column against a subquery of integer primary keys: `ProgrammingError:
      operator does not exist: character varying = bigint`, a 500 on the changelist
      for every non-superuser staff member.
    - For `BenjiSmsBinding`, whose `white_label` is a real FK, it would quietly work,
      and show a white label's bindings to that white label's staff.

    Read-only in every direction: each of these tables has one writer (ai-service for
    transcripts, benefits-api's SMS code for the rest), and a hand-edit would silently
    diverge from what was said or texted.
    """

    always_can_view = False

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        if not self._is_superuser(request):
            return self.model._default_manager.none()
        # SecureAdmin's superuser branch returns the queryset unfiltered.
        return super().get_queryset(request)

    def has_module_permission(self, request: HttpRequest) -> bool:
        # Keeps the section out of the admin nav for tenant staff entirely.
        return self._is_superuser(request)

    def has_view_permission(self, request: HttpRequest, obj: Optional[Model] = None) -> bool:
        return self._is_superuser(request)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Optional[Model] = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Optional[Model] = None) -> bool:
        # Benji history is retained indefinitely and deliberately (see
        # screener/models.py), so there is no routine reason to delete from here, and a
        # click that quietly destroys a household's transcript should not be one
        # keystroke away. A deletion request is a deliberate, scripted operation.
        return False


class AssistantConversationAdmin(SuperuserReadOnlyAdmin):
    """Read-only view of Benji transcripts. Superusers only (see the base class)."""

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


admin.site.register(AssistantConversation, AssistantConversationAdmin)


# Benji SMS (MFB-2435).
#
# NO SEARCH BY PHONE HASH, and none by phone number. Admin search is a GET, so the
# term lands in the URL: in router logs, browser history, and the request data Sentry
# attaches to any error on the page. The privacy companion keeps the hash out of all
# of those. A lookup by number is `manage.py find_benji_sms_phone`, which reads the
# number from a hidden prompt.
#
# The searches that remain are exact lookups on uuids and Twilio SIDs, written out in
# get_search_results: the `=` prefix in search_fields means iexact, which Postgres runs
# as UPPER(col) = UPPER(%s) and cannot answer from the column's index.


class BenjiSmsPhoneAdmin(SuperuserReadOnlyAdmin):
    list_display = ("id", "revoked_at", "shared_until", "created_at")
    ordering = ("-created_at",)
    # phone_hash is shown on the detail page as an opaque value, never in the list.
    readonly_fields = ("phone_hash", "revoked_at", "shared_until", "created_at")


class BenjiSmsBindingAdmin(SuperuserReadOnlyAdmin):
    list_display = ("id", "phone", "screen", "white_label", "status", "consented_at", "created_at")
    list_filter = ("status", "white_label")
    list_select_related = ("phone", "white_label", "conversation")
    # Only so the admin renders the search box: get_search_results replaces the lookup.
    search_fields = ("conversation__screen_uuid",)
    search_help_text = "An exact screen uuid or conversation id."
    ordering = ("-created_at",)
    readonly_fields = (
        "phone",
        "screen",
        "white_label",
        "conversation",
        "status",
        "consented_at",
        "consent_version",
        "created_at",
        "last_inbound_at",
    )

    @admin.display(description="Screen", ordering="conversation__screen_uuid")
    def screen(self, obj: BenjiSmsBinding) -> uuid.UUID:
        return obj.conversation.screen_uuid

    def get_search_results(self, request: HttpRequest, queryset: QuerySet, search_term: str) -> tuple[QuerySet, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        try:
            value = uuid.UUID(term)
        except ValueError:
            return queryset.none(), False
        return queryset.filter(Q(conversation__screen_uuid=value) | Q(conversation_id=value)), False


class BenjiSmsDeliveryAdmin(SuperuserReadOnlyAdmin):
    list_display = ("id", "kind", "delivery_status", "delivery_error_code", "segments", "sent_at", "status_at")
    list_filter = ("kind", "delivery_status")
    # Only so the admin renders the search box: get_search_results replaces the lookup.
    search_fields = ("outbound_sid",)
    search_help_text = "An exact inbound or outbound Twilio message SID."
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

    def get_search_results(self, request: HttpRequest, queryset: QuerySet, search_term: str) -> tuple[QuerySet, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        return queryset.filter(Q(inbound_sid=term) | Q(outbound_sid=term)), False


class BenjiSmsStrangerReplyAdmin(SuperuserReadOnlyAdmin):
    list_display = ("id", "replied_at")
    ordering = ("-replied_at",)
    readonly_fields = ("phone_hash", "replied_at")


admin.site.register(BenjiSmsPhone, BenjiSmsPhoneAdmin)
admin.site.register(BenjiSmsBinding, BenjiSmsBindingAdmin)
admin.site.register(BenjiSmsDelivery, BenjiSmsDeliveryAdmin)
admin.site.register(BenjiSmsStrangerReply, BenjiSmsStrangerReplyAdmin)
