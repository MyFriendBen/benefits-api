"""
Legal status labels, navigator languages and warning calculators each have one list of allowed
values (`programs/allowed_values.py`, and the warning registry). Nothing outside a list can be saved.
"""

from importlib import import_module
from types import SimpleNamespace

from django.apps import apps as global_apps
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import RequestFactory, SimpleTestCase, TestCase

from authentication.models import User
from programs.admin import LegalStatusAdmin, NavigatorLanguageAdmin, WarningMessageAdminForm
from programs.allowed_values import (
    LEGACY_NAVIGATOR_LANGUAGE_CODES,
    USER_SELECTED_LEGAL_STATUSES,
    LegalStatusLabel,
    NavigatorLanguageCode,
)
from programs.models import LegalStatus, Navigator, NavigatorLanguage, WarningMessage
from screener.models import WhiteLabel


class ListTests(SimpleTestCase):
    def test_user_selected_statuses_are_known_labels(self) -> None:
        self.assertEqual(len(USER_SELECTED_LEGAL_STATUSES), 6)
        self.assertLessEqual(set(USER_SELECTED_LEGAL_STATUSES), set(LegalStatusLabel.values))

    def test_every_legacy_language_code_maps_to_a_known_one(self) -> None:
        self.assertLessEqual(set(LEGACY_NAVIGATOR_LANGUAGE_CODES.values()), set(NavigatorLanguageCode.values))
        self.assertFalse(set(LEGACY_NAVIGATOR_LANGUAGE_CODES) & set(NavigatorLanguageCode.values))


class LegalStatusTests(TestCase):
    def test_a_known_label_is_created_once(self) -> None:
        first = LegalStatus.for_label("refugee")

        self.assertEqual(LegalStatus.for_label("refugee"), first)
        self.assertEqual(LegalStatus.objects.filter(status="refugee").count(), 1)

    def test_an_unknown_label_is_refused(self) -> None:
        with self.assertRaisesMessage(ValueError, "legal status 'gc_under5' isn't a label the screener knows"):
            LegalStatus.for_label("gc_under5")

        self.assertFalse(LegalStatus.objects.exists())

    def test_the_database_refuses_an_unknown_label(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            LegalStatus.objects.create(status="other")

    def test_user_selected_comes_from_the_list(self) -> None:
        self.assertTrue(LegalStatus(status="gc_5plus").is_user_selected)
        self.assertFalse(LegalStatus(status="gc_under18_no5").is_user_selected)


class NavigatorLanguageTests(TestCase):
    def test_a_known_code_is_created_once(self) -> None:
        first = NavigatorLanguage.for_code("es")

        self.assertEqual(NavigatorLanguage.for_code("es"), first)

    def test_an_unknown_code_is_refused(self) -> None:
        for code in ("en", "Spanish", "uk"):
            with self.subTest(code=code), self.assertRaisesMessage(ValueError, f"navigator language '{code}'"):
                NavigatorLanguage.for_code(code)

        self.assertFalse(NavigatorLanguage.objects.exists())

    def test_a_snapshot_import_reads_legacy_codes_as_their_replacement(self) -> None:
        self.assertEqual(NavigatorLanguage.for_code("English", accept_legacy=True).code, "en-us")
        self.assertEqual(NavigatorLanguage.for_code("spanish", accept_legacy=True).code, "es")

    def test_the_database_refuses_an_unknown_code(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            NavigatorLanguage.objects.create(code="en")


class WarningCalculatorTests(TestCase):
    def setUp(self) -> None:
        WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")

    def test_a_registered_calculator_saves(self) -> None:
        warning = WarningMessage.objects.new_warning(white_label="co", calculator="_show", external_name="ok")

        self.assertEqual(warning.calculator, "_show")

    def test_new_warning_refuses_an_unregistered_calculator(self) -> None:
        with self.assertRaisesMessage(ValueError, "'cesn' isn't a registered warning calculator"):
            WarningMessage.objects.new_warning(white_label="co", calculator="cesn")

        self.assertFalse(WarningMessage.objects.exists())

    def test_saving_an_unregistered_calculator_is_refused(self) -> None:
        warning = WarningMessage.objects.new_warning(white_label="co", calculator="_show", external_name="ok")
        warning.calculator = "not_registered"

        with self.assertRaisesMessage(ValueError, "'not_registered' isn't a registered warning calculator"):
            warning.save()
        with self.assertRaises(ValidationError):
            warning.clean()

    def test_the_admin_form_offers_only_registered_calculators(self) -> None:
        choices = [value for value, _ in WarningMessageAdminForm.base_fields["calculator"].choices]

        self.assertIn("_show", choices)
        self.assertNotIn("cesn", choices)


class FixedListAdminTests(TestCase):
    def test_superusers_can_view_but_not_add_change_or_delete(self) -> None:
        request = RequestFactory().get("/")
        request.user = User.objects.create_superuser(email_or_cell="admin@example.org", password="x")
        for admin_class, model in ((LegalStatusAdmin, LegalStatus), (NavigatorLanguageAdmin, NavigatorLanguage)):
            admin = admin_class(model, AdminSite())
            with self.subTest(model=model.__name__):
                self.assertTrue(admin.has_view_permission(request))
                self.assertFalse(admin.has_add_permission(request))
                self.assertFalse(admin.has_change_permission(request))
                self.assertFalse(admin.has_delete_permission(request))


class StandardizeNavigatorLanguagesMigrationTests(TestCase):
    """Covers migration 0211's RunPython, which --nomigrations skips."""

    def setUp(self) -> None:
        self.migration = import_module("programs.migrations.0211_standardize_navigator_languages")
        self.schema_editor = SimpleNamespace(connection=connection)
        WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        # The rows this migration cleans up predate the constraint 0212 adds; drop it for this test's
        # transaction so they can exist.
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE programs_navigatorlanguage DROP CONSTRAINT IF EXISTS navigator_language_known_code"
            )

    def navigator(self, name: str, codes: list[str]) -> Navigator:
        navigator = Navigator.objects.new_navigator(white_label="co", name=name)
        navigator.external_name = name
        navigator.save()
        navigator.languages.set([NavigatorLanguage.objects.get_or_create(code=code)[0] for code in codes])
        return navigator

    def codes(self, navigator: Navigator) -> list[str]:
        return sorted(navigator.languages.values_list("code", flat=True))

    def test_legacy_codes_move_to_the_code_they_meant(self) -> None:
        english = self.navigator("english_only", ["English"])
        both = self.navigator("both", ["en", "spanish"])

        self.migration.standardize(global_apps, self.schema_editor)

        self.assertEqual(self.codes(english), ["en-us"])
        self.assertEqual(self.codes(both), ["en-us", "es"])
        self.assertFalse(NavigatorLanguage.objects.filter(code__in=["en", "English", "spanish"]).exists())

    def test_a_navigator_already_on_the_right_code_isnt_linked_twice(self) -> None:
        navigator = self.navigator("already", ["en-us", "en", "english"])

        self.migration.standardize(global_apps, self.schema_editor)

        self.assertEqual(self.codes(navigator), ["en-us"])

    def test_unused_unknown_codes_are_deleted(self) -> None:
        for code in ("uk", "ja", "de"):
            NavigatorLanguage.objects.create(code=code)

        self.migration.standardize(global_apps, self.schema_editor)

        self.assertFalse(NavigatorLanguage.objects.filter(code__in=["uk", "ja", "de"]).exists())

    def test_an_unknown_code_in_use_stops_the_migration(self) -> None:
        self.navigator("ukrainian_help", ["uk"])

        with self.assertRaisesMessage(RuntimeError, "'uk' isn't known and is used by: ukrainian_help"):
            self.migration.standardize(global_apps, self.schema_editor)
