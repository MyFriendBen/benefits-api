"""Which navigators may be linked to which programs, in the admin and the translation import.

A state program takes its own white label's navigators and the federal ones; a federal program
takes any white label's, because the results page shows each state's only to that state.
"""

from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from authentication.models import User
from programs.admin import NavigatorAdmin, ProgramNavigatorInline
from programs.federal import may_link_navigator
from programs.models import Navigator, NavigatorDataController, Program, ProgramNavigator
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
    def _search(self, user: User, model_name: str) -> set[Navigator]:
        request = RequestFactory().get("/", {"model_name": model_name, "field_name": "navigator"})
        request.user = user
        admin = NavigatorAdmin(Navigator, AdminSite())
        queryset, _ = admin.get_search_results(request, admin.get_queryset(request), "")
        return set(queryset)

    def test_partner_admin_is_offered_federal_navigators_on_a_program_page(self) -> None:
        results = self._search(self._user("co_link"), "programnavigator")
        self.assertIn(self.federal_nav, results)
        self.assertIn(self.co_nav, results)
        self.assertNotIn(self.ks_nav, results)

    def test_other_autocompletes_stay_scoped_to_the_admins_white_labels(self) -> None:
        results = self._search(self._user("co_link"), "referrer")
        self.assertNotIn(self.federal_nav, results)


class TestNavigatorImportLinks(_Fixtures):
    """`NavigatorDataController.from_model_data`, which loads navigators from a translations export."""

    def _import(self, navigator: Navigator, *programs: Program) -> None:
        NavigatorDataController(navigator).from_model_data(
            {
                "phone_number": None,
                "counties": [],
                "languages": [],
                "programs": [p.external_name for p in programs],
                "eligibility_programs": [],
                "white_label": navigator.white_label.code,
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
