from django.contrib import admin, messages
from django.db.models import Max, Q, QuerySet
from django.db.models import Field as ModelField
from django import forms
from django.forms import Field as FormField
from django.forms.models import BaseInlineFormSet
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.safestring import SafeString
from django.utils.html import format_html
from unfold.admin import TabularInline
from authentication.admin import SecureAdmin
from .models import (
    LegalStatus,
    Program,
    ProgramCategory,
    ProgramNavigator,
    UrgentNeed,
    UrgentNeedType,
    CategoryIconName,
    Icon,
    FormOption,
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


class ProgramNavigatorInline(TabularInline):
    """
    Sortable inline for managing Navigator ordering within a Program.
    Uses Unfold's drag-and-drop sortable functionality.
    """

    model = ProgramNavigator
    extra = 0
    ordering_field = "order"
    hide_ordering_field = False
    fields = ["navigator", "order"]
    autocomplete_fields = ["navigator"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[ProgramNavigator]:
        """Optimize queries with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related("navigator", "program")

    def get_formset(self, request: HttpRequest, obj: Program | None = None, **kwargs) -> type[BaseInlineFormSet]:
        """
        Auto-assign next sequential order to new navigators.
        Ensures consistent sequential numbering (0, 1, 2, 3...) instead of gaps.

        Edge cases handled:
        - New program with no navigators: starts at 0
        - Empty queryset: safely defaults to 0
        - Multiple concurrent adds: each gets incremented initial value
        - After drag-and-drop renumbering: continues from max
        """
        formset = super().get_formset(request, obj, **kwargs)

        if obj:  # Only for existing programs (not new program creation)
            try:
                # Get the highest current order value from existing navigators
                max_order_result = obj.program_navigators.aggregate(Max("order"))
                max_order = max_order_result.get("order__max")

                # Set initial value for new items
                if max_order is not None:
                    # Continue sequence from highest existing order
                    formset.form.base_fields["order"].initial = max_order + 1
                else:
                    # First navigator for this program
                    formset.form.base_fields["order"].initial = 0
            except (AttributeError, KeyError):
                # Fallback to 0 if anything goes wrong
                formset.form.base_fields["order"].initial = 0

        return formset

    def formfield_for_foreignkey(self, db_field: ModelField, request: HttpRequest, **kwargs) -> FormField | None:
        """Filter navigators by the program's white label"""
        if db_field.name == "navigator":
            obj_id = request.resolver_match.kwargs.get("object_id")
            if obj_id:
                try:
                    program = Program.objects.get(pk=obj_id)
                    kwargs["queryset"] = Navigator.objects.filter(white_label=program.white_label)
                except Program.DoesNotExist:
                    pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProgramAdmin(SecureAdmin):
    search_fields = ("name__translations__text",)
    list_display = ["get_str", "name_abbreviated", "active", "action_buttons"]
    list_editable = ["active"]
    list_filter = [
        "active",
        "low_confidence",
        "show_on_current_benefits",
        "show_in_has_benefits_step",
        "has_calculator",
        "base_program",
    ]

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
    fields = [
        "white_label",
        "name_abbreviated",
        "external_name",
        "year",
        "value_format",
        "category",
        "active",
        "low_confidence",
        "show_on_current_benefits",
        "show_in_has_benefits_step",
        "has_calculator",
        "base_program",
        "legal_status_required",
        "documents",
        "required_programs",
        "excludes_programs",
    ]
    inlines = [ProgramNavigatorInline]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    @admin.display(ordering="name", description="Program")
    def get_str(self, obj: Program) -> str:
        return str(obj) if str(obj).strip() else "unnamed"

    @admin.display(description="Translations")
    def action_buttons(self, obj: Program) -> SafeString:
        return format_html(
            """
            <div class="dropdown">
                <span class="dropdown-btn material-symbols-outlined"> menu </span>
                <div class="dropdown-content">
                    <a href="{}">Name</a>
                    <a href="{}">Description</a>
                    <a href="{}">Website Description</a>
                    <a href="{}">Apply Button Description</a>
                    <a href="{}">Apply Button Link</a>
                    <a href="{}">Estimated Application Time</a>
                    <a href="{}">Estimated Value</a>
                    <a href="{}">Learn More Link</a>
                </div>
            </div>
            """,
            reverse("translation_admin_url", args=[obj.name.id]),
            reverse("translation_admin_url", args=[obj.description.id]),
            reverse("translation_admin_url", args=[obj.website_description.id]),
            reverse("translation_admin_url", args=[obj.apply_button_description.id]),
            reverse("translation_admin_url", args=[obj.apply_button_link.id]),
            reverse("translation_admin_url", args=[obj.estimated_application_time.id]),
            reverse("translation_admin_url", args=[obj.estimated_value.id]),
            reverse("translation_admin_url", args=[obj.learn_more_link.id]),
        )


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
    white_label_filter_horizontal = ("counties", "eligibility_programs")
    filter_horizontal = ("counties", "languages", "eligibility_programs")
    exclude = [
        "name",
        "email",
        "assistance_link",
        "description",
        "programs",
        "programs_ordered",
    ]
    readonly_fields = ["get_associated_programs"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_str(self, obj: Navigator) -> str:
        return str(obj) if str(obj).strip() else "unnamed"

    get_str.admin_order_field = "name"
    get_str.short_description = "Navigator"

    @admin.display(description="Associated Programs")
    def get_associated_programs(self, obj: Navigator) -> str:
        """Display programs this navigator is associated with (read-only)"""
        if not obj.pk:
            return "-"
        program_navs = obj.program_navigators.select_related("program").order_by("order")
        programs = [f"{pn.program.name_abbreviated} (order: {pn.order})" for pn in program_navs]
        return ", ".join(programs) if programs else "No programs associated"

    def action_buttons(self, obj: Navigator) -> SafeString:
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

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_str(self, obj: WarningMessage) -> str:
        return str(obj)

    get_str.admin_order_field = "external_name"
    get_str.short_description = "Name"

    def action_buttons(self, obj: WarningMessage) -> SafeString:

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

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_str(self, obj: UrgentNeed) -> str:
        return str(obj) if str(obj).strip() else "unnamed"

    get_str.admin_order_field = "name"
    get_str.short_description = "Urgent Need"

    def action_buttons(self, obj: UrgentNeed) -> SafeString:
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

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_str(self, obj: Document) -> str:
        return str(obj)

    get_str.admin_order_field = "external_name"
    get_str.short_description = "Document"

    def action_buttons(self, obj: Document) -> SafeString:

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
    search_fields = ("referrer_code", "name")
    list_display = ("referrer_code", "name", "white_label", "show_in_dropdown", "is_partner")
    list_filter = ("white_label", "show_in_dropdown", "is_partner")
    list_editable = ("show_in_dropdown", "is_partner")
    help_texts = {
        "referrer_code": (
            "Used as the <code>referrer</code> URL parameter to pre-fill the referral source field. "
            "Example: <code>https://screener.myfriendben.org/co?referrer=bia</code>"
        ),
        "name": "The label displayed to users in the referral source dropdown.",
        "is_partner": (
            "If checked, this referrer is treated as a named partner organization and grouped under "
            '"Partners" in the screener dropdown. Leave unchecked for generic options like Friend, Google, etc.'
        ),
    }

    def get_form(self, request: HttpRequest, obj: Referrer | None = None, **kwargs) -> type[forms.ModelForm]:
        form = super().get_form(request, obj, **kwargs)
        for field_name, help_text in self.help_texts.items():
            if field_name in form.base_fields:
                form.base_fields[field_name].help_text = help_text
        return form

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
    list_display = ["get_str", "calculator", "field", "get_counties", "active", "action_buttons"]
    list_filter = ["field", "active"]
    filter_horizontal = ("counties",)
    exclude = ["translation"]
    list_editable = ["active"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> QuerySet[TranslationOverride]:
        """Prefetch counties so the list column is one query, not one per row."""
        return super().get_queryset(request).prefetch_related("counties")

    def get_counties(self, obj: TranslationOverride) -> str:
        """Show the county scope in the list so a mis-scoped override is visible."""
        names = [c.name for c in obj.counties.all()]
        return ", ".join(names) if names else "All counties"

    get_counties.short_description = "Counties"

    def get_str(self, obj: TranslationOverride) -> str:
        return str(obj)

    get_str.admin_order_field = "external_name"
    get_str.short_description = "Name"

    def action_buttons(self, obj: TranslationOverride) -> SafeString:
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
    list_display = ["get_str", "external_name", "shared", "action_buttons"]
    exclude = ["name", "description"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> QuerySet[ProgramCategory]:
        # SecureAdmin scopes to white_label__in=[user's white labels], which
        # excludes shared categories because their white_label is null. Any
        # white label admin may see and edit them.
        qs = super(SecureAdmin, self).get_queryset(request)

        if self._is_superuser(request):
            return qs

        return qs.filter(Q(white_label__in=request.user.white_labels.all()) | Q(white_label__isnull=True))

    def has_obj_permission(self, request: HttpRequest, obj: ProgramCategory | None) -> bool:
        # A shared category belongs to no single white label, so grant access to
        # any white label admin rather than falling through to the
        # `obj.white_label in ...` check, which is False for null.
        if obj is not None and obj.white_label is None and not self._is_superuser(request):
            return request.user.white_labels.exists()

        return super().has_obj_permission(request, obj)

    def shared(self, obj: ProgramCategory) -> bool:
        return obj.white_label is None

    shared.boolean = True
    shared.short_description = "Shared"

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict | None = None,
    ) -> HttpResponse:
        # A shared category is a single row used by every white label, so an edit
        # here is not scoped to the editor's own state. Nothing else on the page
        # conveys that, so say it explicitly and name who is affected.
        category = self.get_queryset(request).filter(pk=object_id).first()

        if category is not None and category.white_label is None:
            affected = sorted(
                {
                    code
                    for code in category.programs.values_list("white_label__code", flat=True).distinct()
                    if code is not None
                }
            )
            used_by = ", ".join(affected) if affected else "no white labels yet"
            messages.warning(
                request,
                f"“{category}” is a shared category. Changes to it — including its name and icon — "
                f"apply to every white label that uses it ({used_by}), not just yours.",
            )

        return super().change_view(request, object_id, form_url, extra_context)

    def get_str(self, obj: ProgramCategory) -> str:
        return str(obj)

    get_str.admin_order_field = "external_name"
    get_str.short_description = "Name"

    def action_buttons(self, obj: ProgramCategory) -> SafeString:
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

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_str(self, obj: UrgentNeedType) -> str:
        return str(obj)

    get_str.admin_order_field = "name"
    get_str.short_description = "Name"

    def action_buttons(self, obj: UrgentNeedType) -> SafeString:
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


class IconAdmin(SecureAdmin):
    # Icon has no white_label, so non-superusers would otherwise be denied. Allow view access
    # so white-label admins can use the icon autocomplete from FormOptionAdmin.
    always_can_view = True
    list_display = ["name", "lucide_name", "description"]
    search_fields = ["name", "lucide_name"]
    ordering = ["name"]


class FormOptionAdmin(SecureAdmin):
    list_display = ["white_label", "option_type", "value", "icon", "order", "active"]
    list_filter = ["white_label", "option_type", "active"]
    search_fields = ["value", "white_label__code"]
    ordering = ["white_label", "option_type", "order"]
    autocomplete_fields = ["icon"]


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
admin.site.register(Icon, IconAdmin)
admin.site.register(FormOption, FormOptionAdmin)
