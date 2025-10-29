from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from authentication.admin import SecureAdmin
from .models import (
    LegalStatus,
    Program,
    ProgramCategory,
    UrgentNeed,
    UrgentNeedType,
    CategoryIconName,
    Navigator,
    UrgentNeedFunction,
    FederalPoveryLimit,
    Referrer,
    WarningMessage,
    WebHookFunction,
    UrgentNeedCategory,
    County,
    NavigatorLanguage,
    Document,
    TranslationOverride,
    ExpenseType,
)


class ProgramAdmin(SecureAdmin):
    search_fields = ("name__translations__text",)
    list_display = ["get_str", "name_abbreviated", "active", "action_buttons"]
    white_label_filter_horizontal = [
        "documents",
        "required_programs",
        "excludes_programs",
        "category",
    ]
    filter_horizontal = (
        "legal_status_required",
        "documents",
        "required_programs",
        "excludes_programs",
    )
    exclude = [
        "name",
        "description",
        "description_short",
        "learn_more_link",
        "apply_button_link",
        "apply_button_description",
        "estimated_delivery_time",
        "estimated_application_time",
        "value_type",
        "website_description",
        "estimated_value",
    ]
    list_editable = ["active"]

    fields = (
        "white_label",
        "name_abbreviated",
        "external_name",
        "active",
        "low_confidence",
        "category",
        "legal_status_required",
        "value_format",
        "documents",
        "required_programs",
        "excludes_programs",
    )

    def has_add_permission(self, request):
        return False

    def get_str(self, obj):
        return str(obj) if str(obj).strip() else "unnamed"

    get_str.admin_order_field = "name"
    get_str.short_description = "Program"

    def action_buttons(self, obj):
        name = obj.name
        description = obj.description
        description_short = obj.description_short
        learn_more_link = obj.learn_more_link
        apply_button_link = obj.apply_button_link
        apply_button_description = obj.apply_button_description
        estimated_delivery_time = obj.estimated_delivery_time
        estimated_application_time = obj.estimated_application_time
        value_type = obj.value_type
        website_description = obj.website_description
        estimated_value = obj.estimated_value

        return format_html(
            """
            <div class="dropdown">
                <span class="dropdown-btn material-symbols-outlined"> menu </span>
                <div class="dropdown-content">
                    <a href="{}">Name</a>
                    <a href="{}">Description</a>
                    <a href="{}">Short Description</a>
                    <a href="{}">Learn More Link</a>
                    <a href="{}">Apply Button Link</a>
                    <a href="{}">Apply Button Description</a>
                    <a href="{}">Estimated Delivery Time</a>
                    <a href="{}">Estimated Application Time</a>
                    <a href="{}">Value Type</a>
                    <a href="{}">Website Description</a>
                    <a href="{}">Estimated Value</a>
                </div>
            </div>
            """,
            reverse("translation_admin_url", args=[name.id]),
            reverse("translation_admin_url", args=[description.id]),
            reverse("translation_admin_url", args=[description_short.id]),
            reverse("translation_admin_url", args=[learn_more_link.id]),
            reverse("translation_admin_url", args=[apply_button_link.id]),
            reverse("translation_admin_url", args=[apply_button_description.id]),
            reverse("translation_admin_url", args=[estimated_delivery_time.id]),
            reverse("translation_admin_url", args=[estimated_application_time.id]),
            reverse("translation_admin_url", args=[value_type.id]),
            reverse("translation_admin_url", args=[website_description.id]),
            reverse("translation_admin_url", args=[estimated_value.id]),
        )

    action_buttons.short_description = "Translate:"
    action_buttons.allow_tags = True


class LegalStatusAdmin(SecureAdmin):
    always_can_view = True
    search_fields = ("status",)


class CountiesAdmin(SecureAdmin):
    search_fields = ("name",)


class NavigatorLanguageAdmin(SecureAdmin):
    always_can_view = True
    search_fields = ("code",)


class NavigatorAdmin(SecureAdmin):
    search_fields = ("name__translations__text",)
    list_display = ["get_str", "external_name", "action_buttons"]
    white_label_filter_horizontal = ("programs", "counties")
    filter_horizontal = ("programs", "counties", "languages")
    exclude = [
        "name",
        "email",
        "assistance_link",
        "description",
    ]

    def has_add_permission(self, request):
        return False

    def get_str(self, obj):
        return str(obj) if str(obj).strip() else "unnamed"

    get_str.admin_order_field = "name"
    get_str.short_description = "Navigator"

    def action_buttons(self, obj):
        name = obj.name
        email = obj.email
        assistance_link = obj.assistance_link
        description = obj.description

        return format_html(
            """
            <div class="dropdown">
                <span class="dropdown-btn material-symbols-outlined"> menu </span>
                <div class="dropdown-content">
                    <a href="{}">Name</a>
                    <a href="{}">Email</a>
                    <a href="{}">Assistance Link</a>
                    <a href="{}">Description</a>
                </div>
            </div>
            """,
            reverse("translation_admin_url", args=[name.id]),
            reverse("translation_admin_url", args=[email.id]),
            reverse("translation_admin_url", args=[assistance_link.id]),
            reverse("translation_admin_url", args=[description.id]),
        )

    action_buttons.short_description = "Translate:"
    action_buttons.allow_tags = True


class WarningMessageAdmin(SecureAdmin):
    search_fields = ("external_name",)
    list_display = ["get_str", "calculator", "action_buttons"]
    white_label_filter_horizontal = (
        "programs",
        "counties",
    )
    filter_horizontal = (
        "programs",
        "counties",
        "legal_statuses",
    )
    exclude = ["message", "link_url", "link_text"]

    def has_add_permission(self, request):
        return False

    def get_str(self, obj):
        return str(obj)

    get_str.admin_order_field = "external_name"
    get_str.short_description = "Name"

    def action_buttons(self, obj):

        return format_html(
            """
            <div class="dropdown">
                <span class="dropdown-btn material-symbols-outlined"> menu </span>
                <div class="dropdown-content">
                    <a href="{}">Warning Message</a>
                    <a href="{}">Link</a>
                    <a href="{}">Link Text</a>
                </div>
            </div>
            """,
            reverse("translation_admin_url", args=[obj.message.id]),
            reverse("translation_admin_url", args=[obj.link_url.id]),
            reverse("translation_admin_url", args=[obj.link_text.id]),
        )

    action_buttons.short_description = "Translate:"
    action_buttons.allow_tags = True


class UrgentNeedAdmin(SecureAdmin):
    search_fields = ("name__translations__text",)
    list_display = ["get_str", "external_name", "active", "action_buttons"]
    white_label_filter_horizontal = [
        "counties",
        "category_type",
    ]
    filter_horizontal = (
        "type_short",
        "functions",
        "counties",
        "required_expense_types",
    )
    exclude = [
        "name",
        "description",
        "link",
        "warning",
        "website_description",
        "notification_message",
    ]
    list_editable = ["active"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "white_label",
                    "external_name",
                    "phone_number",
                    "type_short",
                    "category_type",
                    "active",
                    "low_confidence",
                    "show_on_current_benefits",
                    "year",
                    "functions",
                    "counties",
                    "required_expense_types",
                ),
            },
        ),
        (
            "Fields Overview",
            {
                "fields": (),
                "description": (
                    "<b>Type short:</b> A <i>type_short</i> associates a tile option from the immediate need (step-9) page to an urgent "
                    "need. If more than one <i>type_short</i> is selected, the urgent need will be shown in the near-term benefits if either of "
                    "<i>type_short</i> associated tiles is selected.<br>"
                    "<br>"
                    "<b>Category type:</b> A <i>category_type</i> determines the urgent need's category, name and icon.<br>"
                    "<br>"
                    "<b>Required expense types:</b> If none selected, urgent need is shown to all users. "
                    "If any are selected, user must have at least one of these expense types to see this urgent need."
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def get_str(self, obj):
        return str(obj) if str(obj).strip() else "unnamed"

    get_str.admin_order_field = "name"
    get_str.short_description = "Urgent Need"

    def action_buttons(self, obj):
        name = obj.name
        description = obj.description
        link = obj.link
        warning = obj.warning
        website_description = obj.website_description
        notification_message = obj.notification_message

        return format_html(
            """
            <div class="dropdown">
                <span class="dropdown-btn material-symbols-outlined"> menu </span>
                <div class="dropdown-content">
                    <a href="{}">Name</a>
                    <a href="{}">Description</a>
                    <a href="{}">Link</a>
                    <a href="{}">Warning</a>
                    <a href="{}">Website Description</a>
                    <a href="{}">Notification Message</a>
                </div>
            </div>
            """,
            reverse("translation_admin_url", args=[name.id]),
            reverse("translation_admin_url", args=[description.id]),
            reverse("translation_admin_url", args=[link.id]),
            reverse("translation_admin_url", args=[warning.id]),
            reverse("translation_admin_url", args=[website_description.id]),
            reverse("translation_admin_url", args=[notification_message.id]),
        )

    action_buttons.short_description = "Translate:"
    action_buttons.allow_tags = True


class UrgentNeedCategoryAdmin(SecureAdmin):
    always_can_view = True
    search_fields = ("name",)
    fields = ("name",)


class UrgentNeedFunctionAdmin(SecureAdmin):
    always_can_view = True
    search_fields = ("name",)
    fields = ("name",)


class ExpenseTypeAdmin(SecureAdmin):
    always_can_view = True
    search_fields = ("name",)
    fields = ("name",)


class FederalPovertyLimitAdmin(SecureAdmin):
    always_can_view = True
    search_fields = ("year",)


class DocumentAdmin(SecureAdmin):
    search_fields = ("external_name",)
    list_display = ["get_str", "action_buttons"]
    exclude = ["text", "link_url", "link_text"]

    def has_add_permission(self, request):
        return False

    def get_str(self, obj):
        return str(obj)

    get_str.admin_order_field = "external_name"
    get_str.short_description = "Document"

    def action_buttons(self, obj):

        return format_html(
            """
            <div class="dropdown">
                <span class="dropdown-btn material-symbols-outlined"> menu </span>
                <div class="dropdown-content">
                    <a href="{}">Text</a>
                    <a href="{}">Link Url</a>
                    <a href="{}">Link Text</a>
                </div>
            </div>
            """,
            reverse("translation_admin_url", args=[obj.text.id]),
            reverse("translation_admin_url", args=[obj.link_url.id]),
            reverse("translation_admin_url", args=[obj.link_text.id]),
        )

    action_buttons.short_description = "Translate:"
    action_buttons.allow_tags = True


class ReferrerAdmin(SecureAdmin):
    search_fields = ("referrer_code",)
    white_label_filter_horizontal = (
        "primary_navigators",
        "remove_programs",
    )
    filter_horizontal = (
        "webhook_functions",
        "primary_navigators",
        "remove_programs",
    )


class WebHookFunctionsAdmin(SecureAdmin):
    always_can_view = True
    search_fields = ("name",)


class TranslationOverrideAdmin(SecureAdmin):
    search_fields = ("external_name",)
    list_display = ["get_str", "calculator", "active", "action_buttons"]
    white_label_filter_horizontal = ("counties", "program")
    filter_horizontal = ("counties",)
    exclude = ["translation"]
    list_editable = ["active"]

    def has_add_permission(self, request):
        return False

    def get_str(self, obj):
        return str(obj)

    get_str.admin_order_field = "external_name"
    get_str.short_description = "Name"

    def action_buttons(self, obj):
        message = obj.translation

        return format_html(
            """
            <div class="dropdown">
                <span class="dropdown-btn material-symbols-outlined"> menu </span>
                <div class="dropdown-content">
                    <a href="{}">Translation Override</a>
                </div>
            </div>
            """,
            reverse("translation_admin_url", args=[message.id]),
        )

    action_buttons.short_description = "Translate:"
    action_buttons.allow_tags = True


class ProgramCategoryAdmin(SecureAdmin):
    search_fields = ("external_name",)
    list_display = ["get_str", "external_name", "action_buttons"]
    exclude = ["name", "description"]

    def has_add_permission(self, request):
        return False

    def get_str(self, obj):
        return str(obj)

    get_str.admin_order_field = "external_name"
    get_str.short_description = "Name"

    def action_buttons(self, obj):
        return format_html(
            """
            <div class="dropdown">
                <span class="dropdown-btn material-symbols-outlined"> menu </span>
                <div class="dropdown-content">
                    <a href="{}">Name</a>
                    <a href="{}">Description</a>
                </div>
            </div>
            """,
            reverse("translation_admin_url", args=[obj.name.id]),
            reverse("translation_admin_url", args=[obj.description.id]),
        )

    action_buttons.short_description = "Translate:"
    action_buttons.allow_tags = True


class UrgentNeedTypeAdmin(SecureAdmin):
    search_fields = ("name",)
    list_display = ["get_str", "icon", "action_buttons"]

    def has_add_permission(self, request):
        return False

    def get_str(self, obj):
        return str(obj)

    get_str.admin_order_field = "name"
    get_str.short_description = "Name"

    def action_buttons(self, obj):
        return format_html(
            """
            <div class="dropdown">
                <span class="dropdown-btn material-symbols-outlined"> menu </span>
                <div class="dropdown-content">
                    <a href="{}">Name</a>
                </div>
            </div>
            """,
            reverse("translation_admin_url", args=[obj.name.id]),
        )

    action_buttons.short_description = "Translate:"
    action_buttons.allow_tags = True


class CategoryIconNameAdmin(SecureAdmin):
    search_fields = ("name",)


admin.site.register(LegalStatus, LegalStatusAdmin)
admin.site.register(Program, ProgramAdmin)
admin.site.register(County, CountiesAdmin)
admin.site.register(NavigatorLanguage, NavigatorLanguageAdmin)
admin.site.register(Navigator, NavigatorAdmin)
admin.site.register(WarningMessage, WarningMessageAdmin)
admin.site.register(UrgentNeed, UrgentNeedAdmin)
admin.site.register(UrgentNeedCategory, UrgentNeedCategoryAdmin)
admin.site.register(UrgentNeedFunction, UrgentNeedFunctionAdmin)
admin.site.register(ExpenseType, ExpenseTypeAdmin)
admin.site.register(FederalPoveryLimit, FederalPovertyLimitAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(Referrer, ReferrerAdmin)
admin.site.register(WebHookFunction, WebHookFunctionsAdmin)
admin.site.register(TranslationOverride, TranslationOverrideAdmin)
admin.site.register(ProgramCategory, ProgramCategoryAdmin)
admin.site.register(UrgentNeedType, UrgentNeedTypeAdmin)
admin.site.register(CategoryIconName, CategoryIconNameAdmin)
