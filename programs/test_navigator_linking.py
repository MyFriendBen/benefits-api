"""Which navigators may be linked to which programs, in the admin and the translation import.

A state program takes its own white label's navigators and the federal ones; a federal program
takes any white label's, because the results page shows each state's only to that state.
"""

from itertools import product
from types import SimpleNamespace
from typing import Any

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from authentication.models import User
from programs.admin import NavigatorAdmin, ProgramNavigatorInline
from programs.federal import linkable_with, may_link, may_link_navigator
from programs.models import County, Navigator, NavigatorDataController, Program, ProgramNavigator
from screener.models import WhiteLabel


class _Fixtures(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        WhiteLabel.objects.get_or_create(code="federal", defaults={"name": "Federal"})
        WhiteLabel.objects.create(name="CO Test", code="co_link", state_code="CO")
        WhiteLabel.objects.create(name="KS Test", code="ks_link", state_code="KS")
        cls.federal_program = Program.objects.new_program(white_label="federal", name_abbreviated="federal_link")
        cls.co_program = Program.objects.new_program(white_label="co_link", name_abbreviated="co_link_program")
        cls.federal_nav = Navigator.objects.new_navigator("federal", "federal_link_nav")
        cls.co_nav = Navigator.objects.new_navigator("co_link", "co_link_nav")
        cls.ks_nav = Navigator.objects.new_navigator("ks_link", "ks_link_nav")

    def _user(self, *white_label_codes: str, superuser: bool = False) -> User:
        if superuser:
            return User.objects.create_superuser(email_or_cell="super@example.com", password="pw-123456")
        user = User.objects.create_user(email_or_cell="partner@example.com", password="pw-123456")
        user.white_labels.set(WhiteLabel.objects.filter(code__in=white_label_codes))
        return user


class TestMayLinkNavigator(_Fixtures):
    def test_state_program_takes_its_own_and_federal_navigators(self) -> None:
        self.assertTrue(may_link_navigator(self.co_program, "co_link"))
        self.assertTrue(may_link_navigator(self.co_program, "federal"))

    def test_state_program_refuses_another_states_navigator(self) -> None:
        self.assertFalse(may_link_navigator(self.co_program, "ks_link"))

    def test_federal_program_takes_any_white_labels_navigator(self) -> None:
        self.assertTrue(may_link_navigator(self.federal_program, "ks_link"))

    def test_the_filter_and_the_predicate_agree(self) -> None:
        """`linkable_with` is `may_link` as a query, for programs and navigators alike."""
        white_labels = list(WhiteLabel.objects.filter(code__in=["federal", "co_link", "ks_link"]))
        for white_label, navigator in product(white_labels, Navigator.objects.select_related("white_label")):
            with self.subTest(white_label=white_label.code, navigator=navigator.external_name):
                self.assertEqual(
                    Navigator.objects.filter(linkable_with(white_label), pk=navigator.pk).exists(),
                    may_link(white_label.code, navigator.white_label.code),
                )


class TestProgramNavigatorInlineChoices(_Fixtures):
    """The navigator choices on a program's admin page, which are also what saving validates."""

    def _choices(self, program: Program, user: User) -> set[Navigator]:
        request = RequestFactory().get("/")
        request.user = user
        request.resolver_match = SimpleNamespace(kwargs={"object_id": str(program.pk)})
        inline = ProgramNavigatorInline(Program, AdminSite())
        field = inline.formfield_for_foreignkey(ProgramNavigator._meta.get_field("navigator"), request)
        return set(field.queryset)

    def test_superuser_on_federal_program_gets_every_navigator(self) -> None:
        choices = self._choices(self.federal_program, self._user(superuser=True))
        self.assertTrue({self.federal_nav, self.co_nav, self.ks_nav} <= choices)

    def test_superuser_on_state_program_gets_its_own_and_federal(self) -> None:
        choices = self._choices(self.co_program, self._user(superuser=True))
        self.assertIn(self.federal_nav, choices)
        self.assertIn(self.co_nav, choices)
        self.assertNotIn(self.ks_nav, choices)

    def test_partner_admin_on_federal_program_gets_their_states_and_federal(self) -> None:
        choices = self._choices(self.federal_program, self._user("co_link", "federal"))
        self.assertIn(self.federal_nav, choices)
        self.assertIn(self.co_nav, choices)
        self.assertNotIn(self.ks_nav, choices)

    def test_navigator_already_linked_stays_a_valid_choice(self) -> None:
        """A state program linked to another state's navigator before these rules can still be saved."""
        ProgramNavigator.objects.create(program=self.co_program, navigator=self.ks_nav, order=0)
        choices = self._choices(self.co_program, self._user(superuser=True))
        self.assertIn(self.ks_nav, choices)


class TestNavigatorAutocomplete(_Fixtures):
    def _search(self, user: User) -> set[Navigator]:
        request = RequestFactory().get("/", {"model_name": "programnavigator", "field_name": "navigator"})
        request.user = user
        admin = NavigatorAdmin(Navigator, AdminSite())
        queryset, _ = admin.get_search_results(request, admin.get_queryset(request), "")
        return set(queryset)

    def test_partner_admin_is_offered_federal_navigators_on_a_program_page(self) -> None:
        results = self._search(self._user("co_link"))
        self.assertIn(self.federal_nav, results)
        self.assertIn(self.co_nav, results)
        self.assertNotIn(self.ks_nav, results)


class TestFederalNavigatorAccess(_Fixtures):
    """Partner admins may view federal navigators, which their programs show, but not change them."""

    def setUp(self) -> None:
        self.admin = NavigatorAdmin(Navigator, AdminSite())
        self.request = RequestFactory().get("/")
        self.request.user = self._user("co_link")

    def test_partner_admin_lists_federal_navigators(self) -> None:
        listed = set(self.admin.get_queryset(self.request))
        self.assertEqual(listed & {self.federal_nav, self.co_nav, self.ks_nav}, {self.federal_nav, self.co_nav})

    def test_partner_admin_may_view_but_not_change_a_federal_navigator(self) -> None:
        self.assertTrue(self.admin.has_view_permission(self.request, self.federal_nav))
        self.assertFalse(self.admin.has_change_permission(self.request, self.federal_nav))
        self.assertFalse(self.admin.has_delete_permission(self.request, self.federal_nav))

    def test_partner_admin_still_cannot_view_another_states_navigator(self) -> None:
        self.assertFalse(self.admin.has_view_permission(self.request, self.ks_nav))

    def test_partner_admin_still_changes_their_own_navigator(self) -> None:
        self.assertTrue(self.admin.has_change_permission(self.request, self.co_nav))


class TestNavigatorFormChoices(_Fixtures):
    """The counties and required programs a navigator's admin page offers, which saving validates."""

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.ks_program = Program.objects.new_program(white_label="ks_link", name_abbreviated="ks_link_program")
        cls.co_county = County.objects.create(name="Denver County", white_label=cls.co_nav.white_label)
        cls.ks_county = County.objects.create(name="Jackson County", white_label=cls.ks_nav.white_label)

    def _choices(self, navigator: Navigator, field_name: str, user: User) -> set[Any]:
        request = RequestFactory().get("/")
        request.user = user
        form = NavigatorAdmin(Navigator, AdminSite()).get_form(request, navigator)
        return set(form.base_fields[field_name].queryset)

    def test_state_navigator_may_require_its_own_and_federal_programs(self) -> None:
        for user in (self._user(superuser=True), self._user("co_link")):
            with self.subTest(superuser=user.is_superuser):
                choices = self._choices(self.co_nav, "eligibility_programs", user)
                self.assertIn(self.co_program, choices)
                self.assertIn(self.federal_program, choices)
                self.assertNotIn(self.ks_program, choices)
                user.delete()

    def test_state_navigator_offers_only_its_own_counties(self) -> None:
        choices = self._choices(self.co_nav, "counties", self._user(superuser=True))
        self.assertIn(self.co_county, choices)
        self.assertNotIn(self.ks_county, choices)

    def test_navigator_moved_to_federal_keeps_its_states_counties_and_programs(self) -> None:
        self.co_nav.counties.add(self.co_county)
        self.co_nav.eligibility_programs.add(self.co_program)
        self.co_nav.white_label = self.federal_nav.white_label
        self.co_nav.save()
        user = self._user(superuser=True)

        self.assertIn(self.co_county, self._choices(self.co_nav, "counties", user))
        self.assertIn(self.co_program, self._choices(self.co_nav, "eligibility_programs", user))

    def test_a_requirement_chosen_before_these_rules_stays_valid(self) -> None:
        self.co_nav.eligibility_programs.add(self.ks_program)
        self.assertIn(self.ks_program, self._choices(self.co_nav, "eligibility_programs", self._user("co_link")))


class TestNavigatorImportLinks(_Fixtures):
    """`NavigatorDataController.from_model_data`, which loads navigators from a translations export."""

    def _import(
        self,
        navigator: Navigator,
        *programs: Program,
        eligibility_programs: tuple[Program, ...] = (),
        white_label: str = "",
    ) -> None:
        NavigatorDataController(navigator).from_model_data(
            {
                "phone_number": None,
                "counties": [],
                "languages": [],
                "programs": [p.external_name for p in programs],
                "eligibility_programs": [p.external_name for p in eligibility_programs],
                "white_label": white_label or navigator.white_label.code,
            }
        )

    def test_state_navigator_links_to_federal_program(self) -> None:
        self._import(self.co_nav, self.co_program, self.federal_program)
        linked = set(ProgramNavigator.objects.filter(navigator=self.co_nav).values_list("program", flat=True))
        self.assertEqual(linked, {self.co_program.pk, self.federal_program.pk})

    def test_federal_navigator_links_to_state_program(self) -> None:
        self._import(self.federal_nav, self.co_program)
        self.assertTrue(ProgramNavigator.objects.filter(navigator=self.federal_nav, program=self.co_program).exists())

    def test_another_states_navigator_is_deferred(self) -> None:
        with self.assertRaises(NavigatorDataController.DeferCreation):
            self._import(self.ks_nav, self.co_program)

    def test_state_navigator_may_require_a_federal_program(self) -> None:
        self._import(self.co_nav, eligibility_programs=(self.federal_program,))
        self.assertEqual(list(self.co_nav.eligibility_programs.all()), [self.federal_program])

    def test_a_snapshot_from_before_a_move_leaves_the_navigator_on_federal(self) -> None:
        """An export taken while the navigator was still on a state doesn't move it back."""
        self._import(self.federal_nav, self.federal_program, white_label="co_link")
        self.federal_nav.refresh_from_db()
        self.assertEqual(self.federal_nav.white_label.code, "federal")

    def test_a_snapshot_still_sets_a_state_navigators_white_label(self) -> None:
        self._import(self.co_nav, self.federal_program, white_label="ks_link")
        self.co_nav.refresh_from_db()
        self.assertEqual(self.co_nav.white_label.code, "ks_link")
