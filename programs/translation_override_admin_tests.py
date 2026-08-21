"""
Tests for TranslationOverrideAdmin's white-label scoping.

A translation override points at one program and an optional set of counties.
Both pickers used to offer every row in every tenant, so a staffer configuring
an IL override could pick a CO program or a CO county with nothing flagging it.
County matching is exact string equality against `Screen.county` and each white
label spells counties differently ("Cook" in IL, "Cook County" in CO/NC/WA), so a
county from the wrong tenant produces an override that silently never fires.

These tests pin the querysets the admin form offers.
"""

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from programs.admin import TranslationOverrideAdmin
from programs.models import County, Program, TranslationOverride
from screener.models import WhiteLabel


class _Superuser:
    is_superuser = True
    is_active = True
    is_staff = True

    def has_perm(self, *args, **kwargs):
        return True


class TranslationOverrideAdminScopingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.il = WhiteLabel.objects.create(name="IL Admin Test", code="il_admin_test", state_code="IL")
        cls.co = WhiteLabel.objects.create(name="CO Admin Test", code="co_admin_test", state_code="CO")

        cls.il_cook = County.objects.create(name="Cook", white_label=cls.il)
        cls.co_denver = County.objects.create(name="Denver County", white_label=cls.co)

        cls.il_program = Program.objects.new_program("il_admin_test", "il_liheap_admin")
        cls.co_program = Program.objects.new_program("co_admin_test", "co_liheap_admin")

        cls.override = TranslationOverride.objects.new_translation_override(
            "il_admin_test", "_show", "apply_button_link"
        )
        cls.override.program = cls.il_program
        cls.override.save()

    def setUp(self):
        self.admin = TranslationOverrideAdmin(TranslationOverride, AdminSite())
        self.factory = RequestFactory()

    def _request_for_override(self, override_id):
        """A change-page request, with the resolver kwargs the admin reads."""
        request = self.factory.get(f"/admin/programs/translationoverride/{override_id}/change/")
        request.user = _Superuser()
        request.resolver_match = type("M", (), {"kwargs": {"object_id": str(override_id)}})()
        return request

    def test_program_choices_scoped_to_own_white_label(self):
        request = self._request_for_override(self.override.id)
        field = self.admin.formfield_for_foreignkey(TranslationOverride._meta.get_field("program"), request)
        programs = list(field.queryset)
        self.assertIn(self.il_program, programs)
        self.assertNotIn(self.co_program, programs)

    def test_county_choices_scoped_to_own_white_label(self):
        request = self._request_for_override(self.override.id)
        field = self.admin.formfield_for_manytomany(TranslationOverride._meta.get_field("counties"), request)
        counties = list(field.queryset)
        self.assertIn(self.il_cook, counties)
        self.assertNotIn(self.co_denver, counties)

    def test_choices_unscoped_when_no_object_id(self):
        """Without an override in the URL there is no white label to scope to."""
        request = self.factory.get("/admin/programs/translationoverride/")
        request.user = _Superuser()
        request.resolver_match = type("M", (), {"kwargs": {}})()
        field = self.admin.formfield_for_manytomany(TranslationOverride._meta.get_field("counties"), request)
        self.assertIn(self.co_denver, list(field.queryset))

    def test_get_counties_lists_scope(self):
        self.override.counties.set([self.il_cook])
        self.assertEqual(self.admin.get_counties(self.override), "Cook")

    def test_get_counties_reports_unscoped_override(self):
        """An override with no counties applies everywhere — say so explicitly."""
        self.override.counties.clear()
        self.assertEqual(self.admin.get_counties(self.override), "All counties")

    def test_add_permission_still_denied(self):
        """Creation stays in the translations portal, which builds the Translation."""
        request = self.factory.get("/admin/programs/translationoverride/add/")
        request.user = _Superuser()
        self.assertFalse(self.admin.has_add_permission(request))
