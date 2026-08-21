"""
Tests for TranslationOverrideAdmin.

An override points at one program and an optional set of counties. Both pickers
must offer only rows from the override's own white label: county matching is
exact string equality against `Screen.county` and each white label spells its
counties differently ("Cook" in IL, "Cook County" in CO/NC/WA), so a county from
another tenant produces an override that silently never fires.

That scoping comes from `SecureAdmin.get_form`, which narrows every
`ModelChoiceField` on a white-label-bearing model to `obj.white_label`. The test
below goes through `get_form` rather than the `formfield_for_*` hooks so it pins
the guarantee a staffer actually gets, and would fail if that base-class behavior
regressed.
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


class TranslationOverrideAdminTests(TestCase):
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

    def _change_form(self):
        """The form a staffer editing this override actually gets."""
        request = self.factory.get(f"/admin/programs/translationoverride/{self.override.id}/change/")
        request.user = _Superuser()
        return self.admin.get_form(request, obj=self.override)

    def test_change_form_scopes_program_and_counties_to_own_white_label(self):
        """Neither picker may offer another tenant's rows.

        A cross-white-label county is the silent-failure case: it can never equal
        the screen's county, so the override would do nothing with no error.
        """
        form = self._change_form()

        programs = list(form.base_fields["program"].queryset)
        self.assertIn(self.il_program, programs)
        self.assertNotIn(self.co_program, programs)

        counties = list(form.base_fields["counties"].queryset)
        self.assertIn(self.il_cook, counties)
        self.assertNotIn(self.co_denver, counties)

    def test_get_counties_lists_scope(self):
        self.override.counties.set([self.il_cook])
        self.assertEqual(self.admin.get_counties(self.override), "Cook")

    def test_get_counties_reports_unscoped_override(self):
        """An override with no counties applies everywhere — say so explicitly."""
        self.override.counties.clear()
        self.assertEqual(self.admin.get_counties(self.override), "All counties")

    def test_changelist_prefetches_counties(self):
        """The county column must not add a query per row."""
        request = self.factory.get("/admin/programs/translationoverride/")
        request.user = _Superuser()
        self.assertIn("counties", self.admin.get_queryset(request)._prefetch_related_lookups)

    def test_add_permission_still_denied(self):
        """Creation stays in the translations portal, which builds the Translation."""
        request = self.factory.get("/admin/programs/translationoverride/add/")
        request.user = _Superuser()
        self.assertFalse(self.admin.has_add_permission(request))
