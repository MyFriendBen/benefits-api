"""
Legal status labels, navigator languages and warning calculators each have one list of allowed
values (`programs/allowed_values.py`, and the warning registry). Nothing outside a list can be saved.
"""

from importlib import import_module
from types import SimpleNamespace
from typing import Any

from django.apps import apps as global_apps
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import RequestFactory, SimpleTestCase, TestCase

from authentication.models import User
from programs.admin import LegalStatusAdmin, NavigatorLanguageAdmin, WarningMessageAdmin, WarningMessageAdminForm
from programs.allowed_values import (
    USER_SELECTED_LEGAL_STATUSES,
    LegalStatusLabel,
    NavigatorLanguageCode,
)
from programs.models import (
    LegalStatus,
    Navigator,
    NavigatorLanguage,
    Program,
    WarningMessage,
    WarningMessageDataController,
)
from screener.models import WhiteLabel


class ListTests(SimpleTestCase):
    def test_user_selected_statuses_are_known_labels(self) -> None:
        self.assertEqual(len(USER_SELECTED_LEGAL_STATUSES), 6)
        self.assertLessEqual(set(USER_SELECTED_LEGAL_STATUSES), set(LegalStatusLabel.values))


class LegalStatusTests(TestCase):
    def test_a_known_label_is_created_once(self) -> None:
        first = LegalStatus.for_label("refugee")

        self.assertEqual(LegalStatus.for_label("refugee"), first)
        self.assertEqual(LegalStatus.objects.filter(status="refugee").count(), 1)

    def test_an_unknown_label_is_refused(self) -> None:
        with self.assertRaisesMessage(ValueError, "legal status 'gc_under5' isn't a label the screener knows"):
            LegalStatus.for_label("gc_under5")

        self.assertFalse(LegalStatus.objects.exists())

    def test_saving_an_unknown_label_is_refused(self) -> None:
        with self.assertRaisesMessage(ValueError, "legal status 'other' isn't a label the screener knows"):
            LegalStatus.objects.create(status="other")
        with self.assertRaises(ValidationError):
            LegalStatus(status="other").full_clean()

        self.assertFalse(LegalStatus.objects.exists())

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

    def test_saving_an_unknown_code_is_refused(self) -> None:
        with self.assertRaisesMessage(ValueError, "navigator language 'en' isn't one the screener shows"):
            NavigatorLanguage.objects.create(code="en")
        with self.assertRaises(ValidationError):
            NavigatorLanguage(code="en").full_clean()

        self.assertFalse(NavigatorLanguage.objects.exists())


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

    def snapshot_data(self, calculator: str) -> dict:
        return {
            "calculator": calculator,
            "legal_status_required": [{"status": "refugee"}],
            "counties": [],
            "programs": [],
            "white_label": "co",
        }

    def test_a_snapshot_warning_absent_locally_is_created_with_its_calculator(self) -> None:
        WhiteLabel.objects.create(name="Default", code="_default")

        warning = WarningMessageDataController.initialize_instance("from_snapshot", WarningMessage)
        WarningMessageDataController(warning).from_model_data(self.snapshot_data("_tax_unit"))

        warning.refresh_from_db()
        self.assertEqual((warning.calculator, warning.white_label.code), ("_tax_unit", "co"))
        self.assertEqual(list(warning.legal_statuses.values_list("status", flat=True)), ["refugee"])

    def test_a_snapshot_warning_with_an_unregistered_calculator_is_refused(self) -> None:
        WhiteLabel.objects.create(name="Default", code="_default")
        warning = WarningMessageDataController.initialize_instance("from_snapshot", WarningMessage)

        with self.assertRaisesMessage(ValueError, "'renamed_away' isn't a registered warning calculator"):
            WarningMessageDataController(warning).from_model_data(self.snapshot_data("renamed_away"))

    def test_the_admin_form_offers_only_registered_calculators(self) -> None:
        choices = [value for value, _ in WarningMessageAdminForm.base_fields["calculator"].choices]

        self.assertIn("_show", choices)
        self.assertNotIn("cesn", choices)


class WarningAdminFormTests(TestCase):
    """A warning whose calculator was renamed away keeps that name in the form until someone picks
    a registered one, instead of the dropdown silently submitting its first option."""

    def setUp(self) -> None:
        self.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.request = RequestFactory().get("/")
        self.request.user = User.objects.create_superuser(email_or_cell="admin@example.org", password="x")
        self.warning = WarningMessage.objects.new_warning(white_label="co", calculator="_show", external_name="w")
        WarningMessage.objects.filter(pk=self.warning.pk).update(calculator="co_old_name")
        self.warning.refresh_from_db()
        self.admin = WarningMessageAdmin(WarningMessage, AdminSite())

    def form(self, calculator: str) -> Any:
        Form = self.admin.get_form(self.request, self.warning)
        data = {"white_label": self.white_label.pk, "external_name": "w", "calculator": calculator}
        return Form(data=data, instance=self.warning)

    def test_the_stale_calculator_is_the_current_choice(self) -> None:
        Form = self.admin.get_form(self.request, self.warning)
        field = Form(instance=self.warning).fields["calculator"]

        self.assertEqual(field.choices[0], ("co_old_name", "co_old_name (not registered: choose another)"))

    def test_saving_it_unchanged_asks_for_a_registered_calculator(self) -> None:
        form = self.form("co_old_name")

        self.assertFalse(form.is_valid())
        self.assertIn("'co_old_name' isn't a registered warning calculator", form.errors["calculator"][0])

    def test_choosing_a_registered_calculator_saves(self) -> None:
        form = self.form("_tax_unit")

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().calculator, "_tax_unit")


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


class RemoveUnknownLegalStatusesMigrationTests(TestCase):
    """Covers migration 0213's RunPython, which --nomigrations skips."""

    def setUp(self) -> None:
        self.migration = import_module("programs.migrations.0213_remove_unknown_legal_statuses")
        self.schema_editor = SimpleNamespace(connection=connection)
        WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        # Rows as they existed before the check: inserted without `save()`, which refuses them now.
        LegalStatus.objects.bulk_create([LegalStatus(status="other"), LegalStatus(status="citizen")])

    def test_an_unused_unknown_label_is_deleted_and_known_ones_stay(self) -> None:
        self.migration.remove_unknown(global_apps, self.schema_editor)

        self.assertEqual(list(LegalStatus.objects.values_list("status", flat=True)), ["citizen"])

    def test_an_unknown_label_in_use_stops_the_migration(self) -> None:
        program = Program.objects.new_program(white_label="co", name_abbreviated="co_test")
        program.legal_status_required.add(LegalStatus.objects.get(status="other"))

        with self.assertRaisesMessage(RuntimeError, "'other' isn't known and is used by: program co_test"):
            self.migration.remove_unknown(global_apps, self.schema_editor)


class StandardizeNavigatorLanguagesMigrationTests(TestCase):
    """Covers migration 0211's RunPython, which --nomigrations skips."""

    def setUp(self) -> None:
        self.migration = import_module("programs.migrations.0211_standardize_navigator_languages")
        self.schema_editor = SimpleNamespace(connection=connection)
        WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")

    def navigator(self, name: str, codes: list[str]) -> Navigator:
        navigator = Navigator.objects.new_navigator(white_label="co", name=name)
        navigator.external_name = name
        navigator.save()
        navigator.languages.set([self.language(code) for code in codes])
        return navigator

    @staticmethod
    def language(code: str) -> NavigatorLanguage:
        """A language row as it exists before this migration. Saving refuses an unknown code now, so
        the row is inserted without it, the way rows saved before the check were."""
        existing = NavigatorLanguage.objects.filter(code=code).first()
        return existing or NavigatorLanguage.objects.bulk_create([NavigatorLanguage(code=code)])[0]

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
            self.language(code)

        self.migration.standardize(global_apps, self.schema_editor)

        self.assertFalse(NavigatorLanguage.objects.filter(code__in=["uk", "ja", "de"]).exists())

    def test_an_unknown_code_in_use_stops_the_migration(self) -> None:
        self.navigator("ukrainian_help", ["uk"])

        with self.assertRaisesMessage(RuntimeError, "'uk' isn't known and is used by: ukrainian_help"):
            self.migration.standardize(global_apps, self.schema_editor)
