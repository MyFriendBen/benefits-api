"""
A program imported from its v2 spec (it has a `ProgramImportLog` row) offers only Active in the
admin, and its English text can't be edited in the translation editor. Navigator and document
links move off the Program page to "Programs" pickers on the Navigator and Document pages.
"""

from types import SimpleNamespace
from typing import Any

from django.contrib.admin.sites import AdminSite
from django.contrib.messages import get_messages
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from authentication.models import User
from programs.admin import DocumentAdmin, NavigatorAdmin, ProgramAdmin
from programs.models import Document, Navigator, Program, ProgramImportLog, ProgramNavigator
from screener.models import WhiteLabel
from translations.models import Translation


class LockdownBase(TestCase):
    def setUp(self) -> None:
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.nj = WhiteLabel.objects.create(name="New Jersey", code="nj", state_code="NJ")
        self.federal = WhiteLabel.objects.create(name="Federal", code="federal")
        self.superuser = User.objects.create_superuser(email_or_cell="admin@example.org", password="x")
        self.locked = Program.objects.new_program(white_label="co", name_abbreviated="co_locked")
        self.unlocked = Program.objects.new_program(white_label="co", name_abbreviated="co_unlocked")
        self.federal_program = Program.objects.new_program(white_label="federal", name_abbreviated="federal_shared")
        self.nj_program = Program.objects.new_program(white_label="nj", name_abbreviated="nj_other")
        ProgramImportLog.objects.create(
            program=self.locked, white_label_code="co", program_name="co_locked", payload={}, changes=[]
        )

    def request(self, user: User | None = None) -> Any:
        request = RequestFactory().get("/")
        request.user = user or self.superuser
        return request


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class ProgramPageTests(LockdownBase):
    def setUp(self) -> None:
        super().setUp()
        self.admin = ProgramAdmin(Program, AdminSite())

    def test_imported_from_spec_follows_the_import_log(self) -> None:
        self.assertTrue(self.locked.imported_from_spec)
        self.assertFalse(self.unlocked.imported_from_spec)

    def test_a_locked_program_offers_only_active(self) -> None:
        readonly = self.admin.get_readonly_fields(self.request(), self.locked)
        editable = [f for f in self.admin.get_fields(self.request(), self.locked) if f not in readonly]

        self.assertEqual(editable, ["active"])
        self.assertIn("name_abbreviated", readonly)
        self.assertIn("legal_status_required", readonly)

    def test_an_unlocked_program_is_unchanged(self) -> None:
        self.assertEqual(self.admin.get_readonly_fields(self.request(), self.unlocked), [])

    def test_a_locked_federal_program_keeps_the_deactivation_confirmation(self) -> None:
        self.federal_program.active = True
        self.federal_program.save()
        ProgramImportLog.objects.create(
            program=self.federal_program, white_label_code="federal", program_name="federal_shared", payload={}
        )
        readonly = self.admin.get_readonly_fields(self.request(), self.federal_program)
        editable = [f for f in self.admin.get_fields(self.request(), self.federal_program) if f not in readonly]

        self.assertEqual(editable, ["active", "confirm_federal_deactivation"])

    def test_navigators_and_documents_are_off_the_program_page(self) -> None:
        self.assertNotIn("documents", self.admin.get_fields(self.request(), self.unlocked))
        self.assertFalse(self.admin.inlines)

    def test_saving_a_locked_program_changes_only_active(self) -> None:
        self.client.force_login(self.superuser)
        url = reverse("admin:programs_program_change", args=[self.locked.pk])

        page = self.client.get(url)
        response = self.client.post(url, {"active": "on", "name_abbreviated": "renamed", "_save": "Save"})

        self.assertEqual(page.status_code, 200)
        self.assertIn("imported from its spec", " ".join(str(m) for m in get_messages(page.wsgi_request)))
        self.assertEqual(response.status_code, 302)
        self.locked.refresh_from_db()
        self.assertTrue(self.locked.active)
        self.assertEqual(self.locked.name_abbreviated, "co_locked")


class NavigatorPickerTests(LockdownBase):
    def setUp(self) -> None:
        super().setUp()
        self.admin = NavigatorAdmin(Navigator, AdminSite())
        self.navigator = Navigator.objects.new_navigator(white_label="co", name="Help desk")
        ProgramNavigator.objects.create(program=self.nj_program, navigator=self.navigator, order=0)

    def form(self, user: User | None = None) -> Any:
        return self.admin.get_form(self.request(user), self.navigator)(instance=self.navigator)

    def save_links(self, programs: list[Program]) -> None:
        form = SimpleNamespace(
            cleaned_data={"linked_programs": programs}, instance=self.navigator, save_m2m=lambda: None
        )
        self.admin.save_related(self.request(), form, [], True)

    def test_the_picker_offers_linkable_programs_and_existing_links(self) -> None:
        field = self.form().fields["linked_programs"]

        offered = set(field.queryset.values_list("name_abbreviated", flat=True))
        self.assertEqual(offered, {"co_locked", "co_unlocked", "federal_shared", "nj_other"})
        self.assertEqual(field.initial, [self.nj_program.pk])

    def test_a_partner_admin_sees_only_their_white_labels_plus_existing_links(self) -> None:
        partner = User.objects.create_user(email_or_cell="partner@example.org", password="x")
        partner.is_staff = True
        partner.save()
        partner.white_labels.add(self.nj)

        offered = set(self.form(partner).fields["linked_programs"].queryset.values_list("name_abbreviated", flat=True))

        self.assertEqual(offered, {"federal_shared", "nj_other"})

    def test_linking_adds_at_the_end_and_unlinking_removes(self) -> None:
        other = Navigator.objects.new_navigator(white_label="co", name="Other")
        ProgramNavigator.objects.create(program=self.locked, navigator=other, order=0)

        self.save_links([self.locked, self.federal_program])

        links = {
            pn.program.name_abbreviated: pn.order for pn in ProgramNavigator.objects.filter(navigator=self.navigator)
        }
        self.assertEqual(links, {"co_locked": 1, "federal_shared": 0})
        self.assertTrue(ProgramNavigator.objects.filter(navigator=other, program=self.locked, order=0).exists())

    def test_a_link_that_stays_keeps_its_order(self) -> None:
        ProgramNavigator.objects.filter(navigator=self.navigator).update(order=7)

        self.save_links([self.nj_program, self.unlocked])

        self.assertEqual(ProgramNavigator.objects.get(navigator=self.navigator, program=self.nj_program).order, 7)

    def test_a_locked_program_can_still_be_linked_here(self) -> None:
        self.save_links([self.nj_program, self.locked])

        self.assertTrue(ProgramNavigator.objects.filter(navigator=self.navigator, program=self.locked).exists())


class DocumentPickerTests(LockdownBase):
    def setUp(self) -> None:
        super().setUp()
        self.admin = DocumentAdmin(Document, AdminSite())
        self.document = Document.objects.new_document(white_label="co", external_name="co_photo_id")
        self.unlocked.documents.add(self.document)

    def test_the_picker_offers_the_documents_white_label_and_existing_links(self) -> None:
        field = self.admin.get_form(self.request(), self.document)(instance=self.document).fields["linked_programs"]

        offered = set(field.queryset.values_list("name_abbreviated", flat=True))
        self.assertEqual(offered, {"co_locked", "co_unlocked"})
        self.assertEqual(field.initial, [self.unlocked.pk])

    def test_saving_sets_the_linked_programs(self) -> None:
        form = SimpleNamespace(
            cleaned_data={"linked_programs": [self.locked]}, instance=self.document, save_m2m=lambda: None
        )

        self.admin.save_related(self.request(), form, [], True)

        self.assertEqual(list(self.document.program_documents.all()), [self.locked])


class TranslationEditorTests(LockdownBase):
    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.superuser)

    def edit(self, program: Program, lang: str, text: str) -> Any:
        return self.client.post(f"/api/translations/admin/{program.name.id}/{lang}", {"text": text})

    def test_a_locked_programs_english_text_is_refused(self) -> None:
        before = self.locked.name.get_lang("en-us").text

        response = self.edit(self.locked, "en-us", "Renamed in the editor")

        self.assertContains(response, "imported from its spec")
        self.assertEqual(Translation.objects.get(pk=self.locked.name.id).get_lang("en-us").text, before)

    def test_a_locked_programs_other_languages_stay_editable(self) -> None:
        self.edit(self.locked, "es", "Nombre corregido")

        self.assertEqual(Translation.objects.get(pk=self.locked.name.id).get_lang("es").text, "Nombre corregido")

    def test_an_unlocked_programs_english_text_is_editable(self) -> None:
        self.edit(self.unlocked, "en-us", "New name")

        self.assertEqual(Translation.objects.get(pk=self.unlocked.name.id).get_lang("en-us").text, "New name")

    def test_a_locked_programs_translation_cant_be_deleted(self) -> None:
        response = self.client.delete(f"/api/translations/admin/{self.locked.name.id}")

        self.assertContains(response, "imported from its spec")
        self.assertTrue(Translation.objects.filter(pk=self.locked.name.id).exists())


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class PickerPageTests(LockdownBase):
    def test_the_navigator_and_document_pages_render_the_picker(self) -> None:
        navigator = Navigator.objects.new_navigator(white_label="co", name="Help desk")
        document = Document.objects.new_document(white_label="co", external_name="co_photo_id")
        self.client.force_login(self.superuser)

        for url in (
            reverse("admin:programs_navigator_change", args=[navigator.pk]),
            reverse("admin:programs_document_change", args=[document.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'name="linked_programs"')
                self.assertContains(response, "co/co_locked")


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class FederalNavigatorLinkOnlyTests(LockdownBase):
    """A partner admin links a federal navigator to their state's programs from its page, without
    changing its shared fields or another state's links."""

    def setUp(self) -> None:
        super().setUp()
        self.navigator = Navigator.objects.new_navigator(white_label="federal", name="National hotline")
        self.navigator.phone_number = "+13035550100"
        self.navigator.save()
        ProgramNavigator.objects.create(program=self.nj_program, navigator=self.navigator, order=0)
        self.partner = User.objects.create_user(email_or_cell="partner@example.org", password="x")
        self.partner.is_staff = True
        self.partner.save()
        self.partner.white_labels.add(self.co)
        self.client.force_login(self.partner)
        self.url = reverse("admin:programs_navigator_change", args=[self.navigator.pk])

    def test_the_picker_shows_only_the_partners_programs(self) -> None:
        field = (
            NavigatorAdmin(Navigator, AdminSite())
            .get_form(self.request(self.partner), self.navigator)()
            .fields["linked_programs"]
        )

        offered = set(field.queryset.values_list("name_abbreviated", flat=True))
        self.assertEqual(offered, {"co_locked", "co_unlocked", "federal_shared"})
        self.assertEqual(field.initial, [])

    def test_a_partner_links_their_program_and_keeps_other_states_links(self) -> None:
        response = self.client.post(
            self.url, {"linked_programs": [self.unlocked.pk], "phone_number": "+13035559999", "_save": "Save"}
        )

        self.assertEqual(response.status_code, 302)
        linked = set(
            ProgramNavigator.objects.filter(navigator=self.navigator).values_list(
                "program__name_abbreviated", flat=True
            )
        )
        self.assertEqual(linked, {"co_unlocked", "nj_other"})
        self.navigator.refresh_from_db()
        self.assertEqual(str(self.navigator.phone_number), "+13035550100")

    def test_a_partner_unlinks_only_their_own_program(self) -> None:
        ProgramNavigator.objects.create(program=self.unlocked, navigator=self.navigator, order=0)

        self.client.post(self.url, {"_save": "Save"})

        linked = set(
            ProgramNavigator.objects.filter(navigator=self.navigator).values_list(
                "program__name_abbreviated", flat=True
            )
        )
        self.assertEqual(linked, {"nj_other"})
