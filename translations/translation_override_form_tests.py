"""
Tests for the translation override create form in the translations portal.

An override needs four things to actually work: a calculator, the program field
it replaces, the program it belongs to, and (optionally) the counties it applies
to. The form used to collect only the first two, so a new override was born
pointing at no program and applying to every county, and the rest had to be
finished in the Django admin. These tests cover the unified form.

The white label is chosen in the same submission, so program and county choices
cannot be narrowed before submit — cross-white-label combinations are rejected in
clean() instead. That matters most for counties: matching is exact string
equality against `Screen.county`, so a county from another white label can never
match and the override silently never fires.
"""

from django.test import TestCase

from authentication.models import User
from programs.models import County, Program, TranslationOverride
from screener.models import WhiteLabel
from translations.views import TranslationOverrideTranslationAdmin


class _Superuser:
    is_superuser = True
    is_active = True
    is_staff = True


class TranslationOverrideCreateFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.il = WhiteLabel.objects.create(name="IL Form Test", code="il_form_test", state_code="IL")
        cls.co = WhiteLabel.objects.create(name="CO Form Test", code="co_form_test", state_code="CO")

        cls.cook = County.objects.create(name="Cook", white_label=cls.il)
        cls.dupage = County.objects.create(name="DuPage", white_label=cls.il)
        cls.denver = County.objects.create(name="Denver County", white_label=cls.co)

        cls.il_program = Program.objects.new_program("il_form_test", "il_liheap_form")
        cls.co_program = Program.objects.new_program("co_form_test", "co_liheap_form")

    def setUp(self):
        self.view = TranslationOverrideTranslationAdmin()
        self.Form = TranslationOverrideTranslationAdmin.Form

    def _payload(self, **overrides):
        payload = {
            "white_label": "il_form_test",
            "external_name": "il_liheap_cook_apply_link",
            "calculator_name": "_show",
            "field_name": "apply_button_link",
            "program": str(self.il_program.id),
            "counties": [str(self.cook.id)],
        }
        payload.update(overrides)
        return payload

    def _form(self, **overrides):
        return self.Form(self._payload(**overrides), user=_Superuser())

    def test_form_collects_program_and_counties(self):
        form = self._form()
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["program"], self.il_program)
        self.assertEqual(list(form.cleaned_data["counties"]), [self.cook])

    def test_counties_are_optional(self):
        """No counties means the override applies everywhere — a valid choice."""
        form = self._form(counties=[])
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(list(form.cleaned_data["counties"]), [])

    def test_program_is_required(self):
        form = self._form(program="")
        self.assertFalse(form.is_valid())
        self.assertIn("program", form.errors)

    def test_rejects_program_from_another_white_label(self):
        form = self._form(program=str(self.co_program.id))
        self.assertFalse(form.is_valid())
        self.assertIn("program", form.errors)

    def test_rejects_county_from_another_white_label(self):
        """The silent-failure case: a CO county on an IL override never matches."""
        form = self._form(counties=[str(self.denver.id)])
        self.assertFalse(form.is_valid())
        self.assertIn("counties", form.errors)

    def test_rejects_unknown_field_name(self):
        """field_name is a choice now, so a typo cannot reach the database."""
        form = self._form(field_name="aply_button_link")
        self.assertFalse(form.is_valid())
        self.assertIn("field_name", form.errors)

    def test_rejects_unknown_calculator(self):
        form = self._form(calculator_name="_nope")
        self.assertFalse(form.is_valid())
        self.assertIn("calculator_name", form.errors)

    def test_apply_button_link_is_an_offered_field(self):
        """The field this ticket needs has to be selectable."""
        choices = [c[0] for c in self.Form(user=_Superuser()).fields["field_name"].choices]
        self.assertIn("apply_button_link", choices)

    def test_show_calculator_is_offered(self):
        choices = [c[0] for c in self.Form(user=_Superuser()).fields["calculator_name"].choices]
        self.assertIn("_show", choices)

    def test_non_superuser_choices_limited_to_their_white_labels(self):
        """A user who cannot see CO must not be offered CO programs or counties."""
        user = User.objects.create_user(email_or_cell="il-staff@example.org", password="x")
        user.is_staff = True
        user.save()
        user.white_labels.set([self.il])

        form = self.Form(user=user)
        self.assertIn(self.il_program, list(form.fields["program"].queryset))
        self.assertNotIn(self.co_program, list(form.fields["program"].queryset))
        self.assertIn(self.cook, list(form.fields["counties"].queryset))
        self.assertNotIn(self.denver, list(form.fields["counties"].queryset))

    def test_new_object_persists_program_and_counties(self):
        """End to end: the created row comes out fully configured."""
        form = self._form(counties=[str(self.cook.id), str(self.dupage.id)])
        self.assertTrue(form.is_valid(), form.errors)

        override = self.view._new_object(form)
        override.refresh_from_db()

        self.assertEqual(override.program, self.il_program)
        self.assertEqual(override.field, "apply_button_link")
        self.assertEqual(override.calculator, "_show")
        self.assertEqual(override.white_label, self.il)
        self.assertCountEqual([c.name for c in override.counties.all()], ["Cook", "DuPage"])
        self.assertIsNotNone(override.translation)

    def test_new_object_without_counties_applies_everywhere(self):
        form = self._form(counties=[], external_name="il_liheap_statewide")
        self.assertTrue(form.is_valid(), form.errors)

        override = self.view._new_object(form)
        override.refresh_from_db()

        self.assertEqual(list(override.counties.all()), [])
        self.assertEqual(TranslationOverride.objects.filter(pk=override.pk).count(), 1)
