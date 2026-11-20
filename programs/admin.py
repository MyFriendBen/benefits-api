import copy
from typing import Any, Optional

from django.contrib import admin, messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import Max, Q, QuerySet
from django import forms
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.safestring import SafeString
from django.utils.html import format_html
from unfold.widgets import UnfoldBooleanWidget
from authentication.admin import SecureAdmin
from .allowed_values import unknown_warning_calculator, warning_calculator_choices
from .federal import FEDERAL_WHITE_LABEL, is_federal, linkable_with, visible_to_any
from .models import (
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
    Document,
    TranslationOverride,
    ExpenseType,
)


def deactivates_federal_program(form: forms.ModelForm) -> bool:
    """Whether saving `form` switches off a federal program, which hides it from every white label.

    Reads whether the program was federal when the form opened: by `save_model`, `form.instance`
    already carries the submitted white label, so a program moved off federal would read as a
    state one.
    """
    was_federal = getattr(form, "initially_federal", None)
    if was_federal is None:
        was_federal = form.instance.pk is not None and is_federal(form.instance)
    return (
        form.instance.pk is not None
        and was_federal
        and "active" in form.changed_data
        and not form.cleaned_data.get("active")
    )


class ProgramAdminForm(forms.ModelForm):
    confirm_federal_deactivation = forms.BooleanField(
        required=False,
        widget=UnfoldBooleanWidget,
        label="Confirm deactivation",
        help_text="This is a federal program. Unticking Active hides it from every white label, not one state.",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.initially_federal: bool | None = is_federal(self.instance) if self.instance.pk is not None else None

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if deactivates_federal_program(self) and not cleaned_data.get("confirm_federal_deactivation"):
            self.add_error(
                "confirm_federal_deactivation",
                "Deactivating a federal program hides it from every white label. Tick this box to confirm.",
            )
        return cleaned_data


class ProgramChangelistForm(forms.ModelForm):
    """The list page's Active checkbox, locked on active federal programs.

    Switching one off needs the confirmation on the edit form, which a list row can't show.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk is not None and self.instance.active and is_federal(self.instance):
            self.fields["active"].disabled = True


class ProgramAdmin(SecureAdmin):
    form = ProgramAdminForm
    search_fields = ("name__translations__text",)
    list_display = ["get_str", "name_abbreviated", "year_type", "active", "action_buttons"]
    list_editable = ["active"]
    list_select_related = ["white_label"]
    list_filter = [
        "active",
        "year_type",
        "low_confidence",
        "show_on_current_benefits",
        "show_in_has_benefits_step",
        "has_calculator",
        "base_program",
    ]

    white_label_filter_horizontal = [
        "required_programs",
        "excludes_programs",
        "category",
    ]
    filter_horizontal = (
        "legal_status_required",
        "required_programs",
        "excludes_programs",
    )
    fields = [
        "white_label",
        "name_abbreviated",
        "external_name",
        "year",
        "year_type",
        "value_format",
        "category",
        "active",
        "low_confidence",
        "show_on_current_benefits",
        "show_in_has_benefits_step",
        "has_calculator",
        "base_program",
        "legal_status_required",
        "required_programs",
        "excludes_programs",
    ]
    # Navigator and document links are edited from the Navigator and Document pages, so a
    # program imported from its spec can lock this page without locking who it links to.
    # Fields a spec-imported program keeps editable here: switching it on or off is a release
    # decision made per environment, never something the import sets.
    UNLOCKED_FIELDS = ("active", "confirm_federal_deactivation")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_fields(self, request: HttpRequest, obj: Optional[Program] = None) -> list[str]:
        fields = list(super().get_fields(request, obj))
        if obj is not None and is_federal(obj) and obj.active:
            fields.insert(fields.index("active") + 1, "confirm_federal_deactivation")
        return fields

    def get_readonly_fields(self, request: HttpRequest, obj: Optional[Program] = None) -> list[str]:
        """A program imported from its v2 spec takes every field from the spec, except Active."""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.imported_from_spec:
            readonly += [name for name in self.get_fields(request, obj) if name not in self.UNLOCKED_FIELDS]
        return readonly

    def change_view(
        self, request: HttpRequest, object_id: str, form_url: str = "", extra_context: Optional[dict] = None
    ) -> HttpResponse:
        program = self.get_queryset(request).filter(pk=object_id).first()
        if program is not None and program.imported_from_spec:
            messages.info(
                request,
                f"'{program.name_abbreviated}' is imported from its spec in program-ops, so only Active can be "
                "changed here. Other changes go in the spec and are imported. Navigators and documents are linked "
                "from their own pages.",
            )
        return super().change_view(request, object_id, form_url, extra_context)

    def get_changelist_form(self, request: HttpRequest, **kwargs: Any) -> type[forms.ModelForm]:
        return super().get_changelist_form(request, form=ProgramChangelistForm, **kwargs)

    def save_model(self, request: HttpRequest, obj: Program, form: forms.ModelForm, change: bool) -> None:
        deactivated = deactivates_federal_program(form)
        super().save_model(request, obj, form, change)
        if not deactivated:
            return

        # Which state rows replace this one isn't stated: a federal program is prefixed
        # (`federal_trump_account`), so the rows it replaces can't be found by name, and
        # saying "no state version replaces it" from an empty name match would report a
        # safe state that was never checked.
        messages.warning(
            request,
            f"Federal program '{obj.name_abbreviated}' is now inactive and hidden from every white label. "
            "Check that its state versions are active if the program is still meant to be offered.",
        )

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


class CountiesAdmin(SecureAdmin):
    search_fields = ("name",)


class ProgramLinksForm(forms.ModelForm):
    """Adds the "Programs" picker. `ProgramLinksAdmin.get_form` fills its choices per row."""

    linked_programs = forms.ModelMultipleChoiceField(
        queryset=Program.objects.none(),
        required=False,
        label="Programs",
        widget=FilteredSelectMultiple("programs", is_stacked=False),
        help_text="The programs that show this on their program page.",
    )


class ProgramLinksAdmin(SecureAdmin):
    """A "Programs" picker on a shared row's page: which programs show this navigator or document.

    The Program page no longer edits these links, so a program imported from its spec can lock
    that page while its links stay maintained here. The picker offers the programs this row may
    link (`linkable_programs`), narrowed to a partner admin's white labels, plus every program
    already linked, so links made before these rules don't block saving.
    """

    form = ProgramLinksForm
    PROGRAMS_FIELD = "linked_programs"

    def linkable_programs(self, obj: Any) -> Q:
        raise NotImplementedError

    def linked_program_ids(self, obj: Any) -> list[int]:
        raise NotImplementedError

    def set_program_links(self, obj: Any, programs: list[Program]) -> None:
        raise NotImplementedError

    def _set_select_queryset(
        self, field_name: str, field: forms.ModelMultipleChoiceField, obj: Any, request: HttpRequest
    ) -> None:
        # `get_form` sets the picker's choices on this form's own copy of the field.
        if field_name == self.PROGRAMS_FIELD:
            return
        super()._set_select_queryset(field_name, field, obj, request)

    def get_form(self, request: HttpRequest, obj: Any = None, **kwargs: Any) -> type[forms.ModelForm]:
        form = super().get_form(request, obj, **kwargs)
        if self.PROGRAMS_FIELD not in form.base_fields:
            return form
        # The declared field is shared by every form this admin builds; this form gets its own copy.
        field = copy.deepcopy(form.base_fields[self.PROGRAMS_FIELD])
        form.base_fields[self.PROGRAMS_FIELD] = field
        if obj is None or obj.pk is None:
            return form
        linked = Q(pk__in=self.linked_program_ids(obj))
        allowed = self.linkable_programs(obj)
        if not request.user.is_superuser:
            # A partner admin works within their white labels: other states' links are neither
            # shown nor changed (`save_related` keeps them).
            scope = visible_to_any(request.user.white_labels.all())
            allowed &= scope
            linked &= scope
        field.queryset = (
            Program.objects.filter(allowed | linked)
            .select_related("white_label")
            .order_by("white_label__code", "name_abbreviated")
        )
        field.label_from_instance = lambda program: f"{program.white_label.code}/{program.name_abbreviated}"
        field.initial = list(Program.objects.filter(linked).values_list("pk", flat=True))
        return form

    def save_related(self, request: HttpRequest, form: forms.ModelForm, formsets: Any, change: bool) -> None:
        super().save_related(request, form, formsets, change)
        if self.PROGRAMS_FIELD not in form.cleaned_data or form.instance.pk is None:
            return
        programs = list(form.cleaned_data[self.PROGRAMS_FIELD])
        if not request.user.is_superuser:
            # Links to programs outside the partner's white labels weren't offered, so they stay.
            in_scope = set(
                Program.objects.filter(visible_to_any(request.user.white_labels.all())).values_list("pk", flat=True)
            )
            kept = [pk for pk in self.linked_program_ids(form.instance) if pk not in in_scope]
            programs += list(Program.objects.filter(pk__in=kept))
        self.set_program_links(form.instance, programs)


class NavigatorAdmin(ProgramLinksAdmin):
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

    def get_queryset(self, request: HttpRequest) -> QuerySet[Navigator]:
        """A partner admin's navigators plus the federal ones, which they may view but not change.

        Any program may link a federal navigator, so partner admins need to find them in the
        program page's autocomplete and open them from the program. Changing one changes it for
        every white label, so that stays with superusers (`has_change_permission`).
        """
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset | Navigator.objects.filter(white_label__code=FEDERAL_WHITE_LABEL)

    def has_view_permission(self, request: HttpRequest, obj: Optional[Navigator] = None) -> bool:
        if obj is not None and obj.white_label.code == FEDERAL_WHITE_LABEL:
            return True
        return super().has_view_permission(request, obj)

    def _links_only(self, request: HttpRequest, obj: Optional[Navigator]) -> bool:
        """A partner admin on a federal navigator: they may link it to their programs, but its shared
        fields change it for every white label, so those stay with superusers."""
        return (
            obj is not None
            and obj.white_label.code == FEDERAL_WHITE_LABEL
            and not request.user.is_superuser
            and request.user.white_labels.exists()
        )

    def has_change_permission(self, request: HttpRequest, obj: Optional[Navigator] = None) -> bool:
        return self._links_only(request, obj) or super().has_change_permission(request, obj)

    def get_readonly_fields(self, request: HttpRequest, obj: Optional[Navigator] = None) -> list[str]:
        readonly = list(super().get_readonly_fields(request, obj))
        if self._links_only(request, obj):
            readonly += [
                field.name
                for field in [*Navigator._meta.fields, *Navigator._meta.many_to_many]
                if field.editable and not field.auto_created and field.name not in self.exclude
            ]
        return readonly

    def _set_select_queryset(
        self, field_name: str, field: forms.ModelMultipleChoiceField, obj: Optional[Navigator], request: HttpRequest
    ) -> None:
        """Counties and required programs follow the linking rule (`linkable_with`), not the
        navigator's white label alone.

        A state navigator may require a federal program, and a federal navigator may use any white
        label's counties and programs. Rows already chosen stay valid, so a navigator moved to
        `federal` keeps the counties and programs of the state it came from.
        """
        if field_name not in self.white_label_filter_horizontal or obj is None:
            super()._set_select_queryset(field_name, field, obj, request)
            return
        allowed = linkable_with(obj.white_label)
        if not request.user.is_superuser:
            allowed &= visible_to_any(request.user.white_labels.all())
        chosen = Q(pk__in=getattr(obj, field_name).values("pk"))
        field.queryset = field.queryset.filter(allowed | chosen)

    def linkable_programs(self, obj: Navigator) -> Q:
        """The navigator linking rule (`linkable_with`): its own white label's programs, or any
        program for a federal navigator, and federal programs for a state one."""
        return linkable_with(obj.white_label)

    def linked_program_ids(self, obj: Navigator) -> list[int]:
        return list(obj.program_navigators.values_list("program_id", flat=True))

    def set_program_links(self, obj: Navigator, programs: list[Program]) -> None:
        """Add and remove `ProgramNavigator` links. A new link goes last in that program's order;
        links that stay keep their order."""
        wanted = {program.pk for program in programs}
        current = set(self.linked_program_ids(obj))
        ProgramNavigator.objects.filter(navigator=obj, program_id__in=current - wanted).delete()
        for program_id in sorted(wanted - current):
            last = ProgramNavigator.objects.filter(program_id=program_id).aggregate(Max("order"))["order__max"]
            ProgramNavigator.objects.create(program_id=program_id, navigator=obj, order=0 if last is None else last + 1)

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


class WarningMessageAdminForm(forms.ModelForm):
    calculator = forms.ChoiceField(choices=warning_calculator_choices)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # A warning saved before its calculator was renamed or removed keeps that name as its
        # current choice, marked, so the dropdown can't silently fall back to the first option.
        # Saving it unchanged fails the model's check, so someone has to pick a registered one.
        current = self.instance.calculator if self.instance.pk else None
        if current and unknown_warning_calculator(current):
            self.fields["calculator"].choices = [
                (current, f"{current} (not registered: choose another)"),
                *warning_calculator_choices(),
            ]


class WarningMessageAdmin(SecureAdmin):
    form = WarningMessageAdminForm
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

    def _set_select_queryset(
        self,
        field_name: str,
        field: forms.ModelMultipleChoiceField,
        obj: Optional[WarningMessage],
        request: HttpRequest,
    ) -> None:
        """Programs follow the linking rule (`linkable_with`), as a navigator's do.

        A state warning may go on a federal program, where it shows only to screens in its own state
        (`programs.federal.serves_screen`), and a federal warning may go on any program. Programs
        already chosen stay valid. Counties stay on the warning's white label: county names repeat
        across states, so another state's counties would match the wrong screens.
        """
        if field_name != "programs" or obj is None:
            super()._set_select_queryset(field_name, field, obj, request)
            return
        allowed = linkable_with(obj.white_label)
        if not request.user.is_superuser:
            allowed &= visible_to_any(request.user.white_labels.all())
        chosen = Q(pk__in=obj.programs.values("pk"))
        field.queryset = field.queryset.filter(allowed | chosen)

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


class DocumentAdmin(ProgramLinksAdmin):
    search_fields = ("external_name",)
    list_display = ["get_str", "action_buttons"]
    exclude = ["text", "link_url", "link_text"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def linkable_programs(self, obj: Document) -> Q:
        """Programs on the document's own white label, as the Program page's documents picker offered."""
        return Q(white_label_id=obj.white_label_id)

    def linked_program_ids(self, obj: Document) -> list[int]:
        return list(obj.program_documents.values_list("pk", flat=True))

    def set_program_links(self, obj: Document, programs: list[Program]) -> None:
        obj.program_documents.set(programs)

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


class SharedRowAdminMixin:
    """
    Admin behaviour for models whose rows can be shared across white labels.

    A null white_label means the row is shared: one row used by every white
    label. SecureAdmin scopes to white_label__in=[user's white labels], which
    hides shared rows from every non-superuser, so any white label admin may see
    and edit them here. Because an edit is not scoped to the editor's own state,
    the change form says so and names the white labels affected.

    `shared_usage_relation` names the reverse relation whose rows carry the
    white labels using a shared row.
    """

    shared_usage_relation: str
    shared_noun: str

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super(SecureAdmin, self).get_queryset(request)

        if self._is_superuser(request):
            return qs

        return qs.filter(Q(white_label__in=request.user.white_labels.all()) | Q(white_label__isnull=True))

    def has_obj_permission(self, request: HttpRequest, obj: Any) -> bool:
        # A shared row belongs to no single white label, so grant access to any
        # white label admin rather than falling through to the
        # `obj.white_label in ...` check, which is False for null.
        if obj is not None and obj.white_label is None and not self._is_superuser(request):
            return request.user.white_labels.exists()

        return super().has_obj_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        # Deleting a shared row strips it from every white label, so only a
        # superuser may.
        if obj is not None and obj.white_label is None and not self._is_superuser(request):
            return False

        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        readonly = tuple(super().get_readonly_fields(request, obj))

        # Changing white_label moves a row between shared and scoped, which
        # hides it from, or exposes it to, every other white label.
        if not self._is_superuser(request):
            readonly += ("white_label",)

        return readonly

    def shared(self, obj: Any) -> bool:
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
        row = self.get_queryset(request).filter(pk=object_id).first()

        if row is not None and row.white_label is None:
            usage = getattr(row, self.shared_usage_relation)
            affected = sorted(
                {code for code in usage.values_list("white_label__code", flat=True).distinct() if code is not None}
            )
            used_by = ", ".join(affected) if affected else "no white labels yet"
            messages.warning(
                request,
                f"“{row}” is a shared {self.shared_noun}. Changes to it — including its name and icon — "
                f"apply to every white label that uses it ({used_by}), not just yours.",
            )

        return super().change_view(request, object_id, form_url, extra_context)


class ProgramCategoryAdmin(SharedRowAdminMixin, SecureAdmin):
    search_fields = ("external_name",)
    list_display = ["get_str", "external_name", "shared", "action_buttons"]
    exclude = ["name", "description"]
    shared_usage_relation = "programs"
    shared_noun = "category"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

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


class UrgentNeedTypeAdmin(SharedRowAdminMixin, SecureAdmin):
    search_fields = ("external_name",)
    list_display = ["get_str", "external_name", "icon", "shared", "action_buttons"]
    shared_usage_relation = "urgent_needs"
    shared_noun = "urgent need type"

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


admin.site.register(Program, ProgramAdmin)
admin.site.register(County, CountiesAdmin)
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
