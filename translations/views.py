from django.core.paginator import Paginator
from django.shortcuts import render
from django.conf import settings
from authentication.models import User
from screener.models import WhiteLabel
from .models import Translation, HistoricalTranslation
from simple_history.utils import update_change_reason
from rest_framework.response import Response
from rest_framework import views
from django import forms
from django.http import (
    HttpResponseBadRequest,
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseRedirect,
)
from django.db.models import ProtectedError
from django.db import models
from programs.models import (
    Program,
    Navigator,
    ProgramCategory,
    UrgentNeed,
    UrgentNeedType,
    CategoryIconName,
    Document,
    WarningMessage,
    TranslationOverride,
)
from phonenumber_field.formfields import PhoneNumberField
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from integrations.services.google_translate.integration import Translate
from django.urls import path


class TranslationView(views.APIView):
    def get(self, request):
        language = request.query_params.get("lang")
        all_langs = [lang["code"] for lang in settings.PARLER_LANGUAGES[None]]

        if language in all_langs:
            translations = Translation.objects.all_translations([language])
        else:
            translations = Translation.objects.all_translations()

        return Response(translations)


class NewTranslationForm(forms.Form):
    label = forms.CharField(max_length=128, widget=forms.TextInput(attrs={"class": "input"}))
    default_message = forms.CharField(
        widget=forms.Textarea(attrs={"name": "text", "rows": 3, "cols": 50, "class": "textarea"})
    )


@login_required(login_url="/admin/login")
@staff_member_required
def admin_view(request):
    # don't let non super users view/create the main translations
    if not request.user.is_superuser:
        return HttpResponseRedirect("/api/translations/admin/programs")

    if request.method == "GET":
        translations = Translation.objects.all().order_by("id")
        # Display 50 translations per page
        paginator = Paginator(translations, 50)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        for translation in page_obj:
            used_by_info = translation.used_by

            translation.entry_id = used_by_info["id"]
            translation.model_name = used_by_info["model_name"]
            translation.field_name = used_by_info["field_name"]
            translation.display_name = used_by_info["display_name"]

        context = {"page_obj": page_obj}

        return render(request, "main.html", context)
    elif request.method == "POST":
        form = NewTranslationForm(request.POST)
        if form.is_valid():
            text = form["default_message"].value()
            translation = Translation.objects.add_translation(form["label"].value(), text)

            auto_translations = Translate().bulk_translate(["__all__"], [text])[text]

            for [language, auto_text] in auto_translations.items():
                Translation.objects.edit_translation_by_id(translation.id, language, auto_text, False)

            response = HttpResponse()
            response.headers["HX-Redirect"] = f"/api/translations/admin/{translation.id}"
            return response
        return HttpResponseBadRequest()


@login_required(login_url="/admin/login")
@staff_member_required
def create_translation_view(request):
    # don't let non super users create the main translations
    if not request.user.is_superuser:
        return HttpResponseRedirect("/api/translations/admin/programs")

    context = {"form": NewTranslationForm(), "route": "/api/translations/admin"}

    return render(request, "util/create_form.html", context)


@login_required(login_url="/admin/login")
@staff_member_required
def filter_view(request):
    # don't let non super users view the main translations
    if not request.user.is_superuser:
        return HttpResponseRedirect("/api/translations/admin/programs")

    translations = Translation.objects.filter(label__icontains=request.GET.get("label", "")).translated(
        text__icontains=request.GET.get("text", "")
    )
    paginator = Paginator(translations, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for translation in page_obj:
        used_by_info = translation.used_by

        translation.entry_id = used_by_info["id"]
        translation.model_name = used_by_info["model_name"]
        translation.field_name = used_by_info["field_name"]
        translation.display_name = used_by_info["display_name"]

    context = {"page_obj": page_obj}

    return render(request, "translations.html", context)


class TranslationForm(forms.Form):
    text = forms.CharField(
        widget=forms.Textarea(attrs={"name": "text", "rows": 3, "cols": 50, "class": "textarea"}), required=False
    )


class LabelForm(forms.Form):
    label = forms.CharField(max_length=128, widget=forms.TextInput(attrs={"class": "input"}), label="Label Title")
    active = forms.BooleanField(required=False)
    no_auto = forms.BooleanField(required=False, label="Exclude all from auto-translate")


def has_translation_access(translation: Translation, user: User) -> bool:
    if user.is_superuser:
        return True
    reverse_instances = translation.get_reverse_instances()

    if len(reverse_instances) == 0:
        return False

    allowed_white_labels = user.white_labels.all().values_list("id", flat=True)

    # only allow acces if the user can access all the models it is attached to
    for reverse in reverse_instances:
        if reverse.instance.white_label.id not in allowed_white_labels:
            return False

    return True


@login_required(login_url="/admin/login")
@staff_member_required
def translation_view(request, id=0):
    translation = Translation.objects.prefetch_related("translations").get(pk=id)

    if not has_translation_access(translation, request.user):
        return HttpResponseRedirect("/api/translations/admin/programs")

    if request.method == "GET":
        langs = [lang["code"] for lang in settings.PARLER_LANGUAGES[None]]

        # sorted in the order of settings.LANGUAGES
        translations = {
            lang_code: TranslationForm(
                {"text": next((t.text for t in translation.translations.all() if t.language_code == lang_code), "")}
            )
            for lang_code, _ in settings.LANGUAGES
        }

        all_history = translation.history.all().order_by("history_date")

        updated_dates = {}
        for record in all_history:
            if record.changed_text:
                updated_dates[record.affected_language] = record.history_date

        for lang in langs:
            if lang not in translations:
                translations[lang] = TranslationForm()

        context = {
            "translation": translation,
            "langs": translations,
            "label_form": LabelForm(
                {"label": translation.label, "active": translation.active, "no_auto": translation.no_auto}
            ),
            "updated_dates": updated_dates,
        }

        return render(request, "edit/main.html", context)
    elif request.method == "POST":
        form = LabelForm(request.POST)
        if form.is_valid():
            translation.label = form["label"].value()
            translation.active = form["active"].value()
            translation.no_auto = form["no_auto"].value()
            translation.save()

            context = {
                "form": LabelForm(
                    {"label": translation.label, "active": translation.active, "no_auto": translation.no_auto}
                ),
            }
            return render(request, "edit/label_form.html", context)
    elif request.method == "DELETE":
        try:
            translation.delete()
        except ProtectedError:
            return render(
                request,
                "error.html",
                {
                    "error_message": "Please delete the program that this translation is attached to if you want to delete this translation"
                },
            )
        response = HttpResponse()
        response.headers["HX-Redirect"] = "/api/translations/admin"
        return response


@login_required(login_url="/admin/login")
@staff_member_required
def edit_translation(request, id=0, lang="en-us"):
    translation = Translation.objects.get(pk=id)

    if not has_translation_access(translation, request.user):
        return HttpResponseRedirect("/api/translations/admin/programs")

    if request.method == "POST":
        form = TranslationForm(request.POST)
        auto_translate_check = request.POST.get("auto_translate_check", False)
        excluded_langs = request.POST.getlist("excluded_languages", [])

        languages = [l for l in Translate.languages if l not in excluded_langs]

        if form.is_valid():
            text = form["text"].value()
            translation = Translation.objects.edit_translation_by_id(id, lang, text)

            if lang == settings.LANGUAGE_CODE:
                if not translation.no_auto:
                    if not auto_translate_check:
                        Translation.objects.edit_translation_by_id(id, lang, text, False)
                    else:
                        translations = Translate().bulk_translate(languages, [text])[text]

                        for language in languages:
                            translated_text = text if translation.no_auto else translations[language]
                            Translation.objects.edit_translation_by_id(id, language, translated_text, False)

            parent = Translation.objects.get(pk=id)
            all_history = parent.history.all().order_by("history_date")
            updated_dates = {}
            for record in all_history:
                if record.changed_text:
                    updated_dates[record.affected_language] = record.history_date

            # sorted in the order of settings.LANGUAGES
            forms = {
                lang_code: TranslationForm(
                    {"text": next((t.text for t in parent.translations.all() if t.language_code == lang_code), "")}
                )
                for lang_code, _ in settings.LANGUAGES
            }
            context = {
                "translation": parent,
                "langs": forms,
                "updated_dates": updated_dates,
            }
            return render(request, "edit/langs.html", context)


def get_white_label_choices():
    return [(w.code, w.name) for w in WhiteLabel.objects.exclude(code="_default").order_by("name")]


def get_urgent_need_icon_choices():
    icons = CategoryIconName.objects.all().order_by("name")
    return [(icon.name, icon.name) for icon in icons]


class WhiteLabelForm(forms.Form):
    white_label = forms.ChoiceField(choices=get_white_label_choices, widget=forms.Select(attrs={"class": "input"}))

    def __init__(self, *args, user: User = None, **kwargs):
        super().__init__(*args, **kwargs)

        # make the white_label be the last field
        self.order_fields(sorted(self.fields, key=lambda f: 1 if f == "white_label" else 0))

        if user.is_superuser:
            return

        allowed_white_label_codes = user.white_labels.all().values_list("code", flat=True)

        white_label_field = self.fields["white_label"]
        white_label_field.choices = [c for c in white_label_field.choices if c[0] in allowed_white_label_codes]


class TranslationAdminViews:
    name = ""
    ordering_field = "external_name"

    class Form(WhiteLabelForm):
        pass

    # assume the model has a white_label foreign key, and an external_name
    Model = models.Model

    def _list_view(self, request):
        objects = self._model_white_label_query_set(request.user).order_by(self.ordering_field)

        paginator = Paginator(objects, 50)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {"page_obj": page_obj}

        return render(request, f"{self.name}/main.html", context)

    def _add_view(self, request):
        form = self.Form(request.POST, user=request.user)
        if form.is_valid():
            new_object = self._new_object(form)
            response = HttpResponse()
            response.headers["HX-Redirect"] = f"/api/translations/admin/{self.name}/{new_object.id}"
            return response
        return HttpResponseBadRequest()

    def _new_object(self, form: Form) -> models.Model:
        raise NotImplemented(f"Please add the `new_object` method for the '{self.name}' translations admin")

    def _add_form_view(self, request):
        context = {"form": self.Form(user=request.user), "route": f"/api/translations/admin/{self.name}"}

        return render(request, "util/create_form.html", context)

    def _object_page_view(self, request, id=0):
        page_object = self._model_white_label_query_set(request.user).get(pk=id)
        context = {"object": page_object}

        return render(request, f"{self.name}/page.html", context)

    def _filter_view(self, request, **kwargs):
        obj_id = kwargs.get("id")
        if obj_id:
            objects = self._filter_query_set_by_id(request, obj_id).distinct().order_by(self.ordering_field)
        else:
            objects = self._filter_query_set(request).distinct().order_by(self.ordering_field)

        paginator = Paginator(objects, 50)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {"page_obj": page_obj}

        return render(request, f"{self.name}/list.html", context)

    def _filter_query_set(self, request):
        raise NotImplemented(f"Please add the `filter_query_set` method for the '{self.name}' translations admin")

    def _filter_query_set_by_id(self, request, obj_id):
        raise NotImplemented(
            f"Please add the `_filter_query_set_by_id` method for the '{self.name}' translations admin"
        )

    def _model_white_label_query_set(self, user: User):
        query_set = self.Model.objects.all()

        if user.is_superuser:
            return query_set

        return query_set.filter(white_label__in=user.white_labels.all())

    def _wapper(self, func):
        @login_required(login_url="/admin/login")
        @staff_member_required
        def check_white_label_access(*args, **kwargs):
            return func(*args, **kwargs)

        return check_white_label_access

    def urls(self):
        return [
            path(f"admin/{self.name}", self._wapper(self._list_router)),
            path(f"admin/{self.name}/filter", self._wapper(self._filter_router)),
            path(f"admin/{self.name}/create", self._wapper(self._form_router)),
            path(f"admin/{self.name}/<int:id>", self._wapper(self._page_router)),
        ]

    def _list_router(self, request, *args, **kwargs):
        if request.method == "GET":
            return self._list_view(request, *args, **kwargs)
        elif request.method == "POST":
            return self._add_view(request, *args, **kwargs)

        return HttpResponseNotFound()

    def _filter_router(self, request, *args, **kwargs):
        if request.method == "GET":
            return self._filter_view(request, *args, **kwargs)

        return HttpResponseNotFound()

    def _page_router(self, request, *args, **kwargs):
        if request.method == "GET":
            return self._object_page_view(request, *args, **kwargs)

        return HttpResponseNotFound()

    def _form_router(self, request, *args, **kwargs):
        if request.method == "GET":
            return self._add_form_view(request, *args, **kwargs)

        return HttpResponseNotFound()


class ProgramTranslationAdmin(TranslationAdminViews):
    name = "programs"

    class Form(WhiteLabelForm):
        name_abbreviated = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "input"}))

    Model = Program

    def _new_object(self, form: Form) -> models.Model:
        return self.Model.objects.new_program(form["white_label"].value(), form["name_abbreviated"].value())

    def _filter_query_set(self, request):
        return self._model_white_label_query_set(request.user).filter(
            name__translations__text__icontains=request.GET.get("name", "")
        )


class NavigatorTranslationAdmin(TranslationAdminViews):
    name = "navigators"

    class Form(WhiteLabelForm):
        label = forms.CharField(max_length=50, widget=forms.TextInput(attrs={"class": "input"}))
        phone_number = PhoneNumberField(required=False, widget=forms.TextInput(attrs={"class": "input"}))

    Model = Navigator

    def _new_object(self, form: Form) -> models.Model:
        return self.Model.objects.new_navigator(
            form["white_label"].value(),
            form["label"].value(),
            form["phone_number"].value(),
        )

    def _filter_query_set(self, request):
        return self._model_white_label_query_set(request.user).filter(
            name__translations__text__icontains=request.GET.get("name", "")
        )


class UrgentNeedTranslationAdmin(TranslationAdminViews):
    name = "urgent_needs"

    class Form(WhiteLabelForm):
        label = forms.CharField(max_length=50, widget=forms.TextInput(attrs={"class": "input"}))
        phone_number = PhoneNumberField(required=False, widget=forms.TextInput(attrs={"class": "input"}))

    Model = UrgentNeed

    def _new_object(self, form: Form) -> models.Model:
        return self.Model.objects.new_urgent_need(
            form["white_label"].value(),
            form["label"].value(),
            form["phone_number"].value(),
        )

    def _filter_query_set(self, request):
        return self._model_white_label_query_set(request.user).filter(
            name__translations__text__icontains=request.GET.get("name", "")
        )


class DocumentTranslationAdmin(TranslationAdminViews):
    name = "documents"

    class Form(WhiteLabelForm):
        external_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "input"}))

    Model = Document

    def _new_object(self, form: Form) -> models.Model:
        return self.Model.objects.new_document(form["white_label"].value(), form["external_name"].value())

    def _filter_query_set(self, request):
        return self._model_white_label_query_set(request.user).filter(
            external_name__contains=request.GET.get("name", "")
        )


class WarningMessageTranslationAdmin(TranslationAdminViews):
    name = "warning_messages"

    class Form(WhiteLabelForm):
        external_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "input"}))
        calculator_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "input"}))

    Model = WarningMessage

    def _new_object(self, form: Form) -> models.Model:
        return self.Model.objects.new_warning(
            form["white_label"].value(), form["calculator_name"].value(), form["external_name"].value()
        )

    def _filter_query_set(self, request):
        return self._model_white_label_query_set(request.user).filter(
            external_name__contains=request.GET.get("name", "")
        )


class TranslationOverrideTranslationAdmin(TranslationAdminViews):
    name = "translation_overrides"

    class Form(WhiteLabelForm):
        external_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "input"}))
        calculator_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "input"}))
        field_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "input"}))

    Model = TranslationOverride

    def _new_object(self, form: Form) -> models.Model:
        return self.Model.objects.new_translation_override(
            form["white_label"].value(),
            form["calculator_name"].value(),
            form["field_name"].value(),
            form["external_name"].value(),
        )

    def _filter_query_set(self, request):
        return self._model_white_label_query_set(request.user).filter(
            external_name__contains=request.GET.get("name", "")
        )


class ProgramCategoryTranslationAdmin(TranslationAdminViews):
    name = "program_categories"

    class Form(WhiteLabelForm):
        external_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "input"}))
        icon = forms.ChoiceField(choices=get_urgent_need_icon_choices, widget=forms.Select(attrs={"class": "input"}))

    Model = ProgramCategory

    def _new_object(self, form: Form) -> models.Model:
        return self.Model.objects.new_program_category(
            form["white_label"].value(), form["external_name"].value(), form["icon"].value()
        )

    def _filter_query_set(self, request):
        return self._model_white_label_query_set(request.user).filter(
            external_name__contains=request.GET.get("name", "")
        )


class UrgentNeedTypeTranslationAdmin(TranslationAdminViews):
    name = "urgent_need_types"
    ordering_field = "icon__name"

    class Form(WhiteLabelForm):
        external_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"class": "input"}))
        icon = forms.ChoiceField(choices=get_urgent_need_icon_choices, widget=forms.Select(attrs={"class": "input"}))

    Model = UrgentNeedType

    def _new_object(self, form: Form) -> models.Model:
        return self.Model.objects.new_urgent_need_type(
            form["white_label"].value(), form["external_name"].value(), form["icon"].value()
        )

    def _filter_query_set(self, request):
        query = request.GET.get("name", "")
        return self._model_white_label_query_set(request.user).filter(icon__name__contains=query).order_by("icon")


class TranslationHistoryTranslationAdmin(TranslationAdminViews):
    name = "translation_history"
    ordering_field = "-history_date"

    class Form(WhiteLabelForm):
        pass

    Model = HistoricalTranslation

    def urls(self):
        return [
            path(f"admin/{self.name}/<int:id>", self._wapper(self._list_router)),
            path(f"admin/{self.name}/<int:id>/filter", self._wapper(self._filter_router)),
            path(
                f"admin/{self.name}/revert/<int:history_id>",
                self._wapper(self.revert_translation),
                name="revert_translation",
            ),
        ]

    def revert_translation(self, request, history_id):
        historical_record = HistoricalTranslation.objects.get(history_id=history_id)
        instance = historical_record.instance
        lang = historical_record.affected_language

        Translation.objects.edit_translation_by_id(
            instance.id,
            lang,
            historical_record.original_text,
            historical_record.edit_type,
        )

        update_change_reason(instance, f"Reverted to history ID {history_id} for '{lang}'")

        instance.save()
        return HttpResponseRedirect(
            f"/api/translations/admin/translation_history/{instance.id}?lang={historical_record.affected_language}"
        )

    def _list_view(self, request, id):
        try:
            translation = Translation.objects.get(pk=id)
        except Translation.DoesNotExist:
            return HttpResponseNotFound()

        if not has_translation_access(translation, request.user):
            return HttpResponseRedirect("/api/translations/admin/programs")

        lang = request.GET.get("lang")

        all_history = translation.history.filter(changed_text__isnull=False).order_by(self.ordering_field)

        if lang:
            all_history = all_history.filter(affected_language=lang)

        paginator = Paginator(all_history, 25)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "translation": translation,
            "page_obj": page_obj,
        }
        return render(request, f"{self.name}/main.html", context)

    def _filter_query_set_by_id(self, request, obj_id):
        return (
            self._model_white_label_query_set(request.user)
            .filter(original_text__icontains=request.GET.get("name", ""))
            .order_by(self.ordering_field)
        )
