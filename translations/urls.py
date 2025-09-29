from django.urls import path
from . import views


urlpatterns = [
    path("", views.TranslationView.as_view()),
    path("admin", views.admin_view, name="translations_api_url"),
    path("admin/filter", views.filter_view),
    path("admin/create", views.create_translation_view),
    path("admin/<int:id>", views.translation_view, name="translation_admin_url"),
    path("admin/<int:id>/<str:lang>", views.edit_translation),
    *views.ProgramTranslationAdmin().urls(),
    *views.NavigatorTranslationAdmin().urls(),
    *views.UrgentNeedTranslationAdmin().urls(),
    *views.DocumentTranslationAdmin().urls(),
    *views.WarningMessageTranslationAdmin().urls(),
    *views.TranslationOverrideTranslationAdmin().urls(),
    *views.ProgramCategoryTranslationAdmin().urls(),
    *views.UrgentNeedTypeTranslationAdmin().urls(),
    *views.TranslationHistoryTranslationAdmin().urls(),
]
