"""Programs under the `federal` white label are shown to every white label.

A federal row is prefixed (`federal_trump_account`), so it does not share a name with the
state rows it replaces, and moving a program deactivates those state rows. These tests cover
the read paths that union federal programs in (results, current benefits, the has-benefits
step, the current-benefits page) and the collision rule for the un-prefixed rows that predate
the prefix, where a name still active on both sides is logged and resolved to the federal row
rather than raised. Switching a federal program off in the admin needs a confirmation,
because it hides the program from every white label.

Calculators are stubbed through `Program.eligibility`: what is under test is which rows the
results page fetches and publishes, not any program's rule.
"""

import json
from typing import Any, Optional
from unittest.mock import patch

from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.auth.models import Permission
from django.db.models import Model
from django.forms import ModelForm
from django.forms.models import model_to_dict
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from authentication.models import User
from configuration.white_labels import state_options
from programs.federal import FEDERAL_WHITE_LABEL
from programs.framework.base import Eligibility
from programs.admin import ProgramAdmin, ReferrerAdmin, WarningMessageAdmin
from programs.models import FederalPoveryLimit, Program, ProgramCategory, Referrer, WarningMessage
from programs.programs.testing_fixtures.households import add_income, add_member
from programs.serializers import ProgramCategorySerializer
from screener.models import CurrentBenefit, EligibilitySnapshot, Screen, WhiteLabel
from screener.serializers import ScreenSerializer, _derived_current_benefit_names, _write_current_benefits
from screener.views import eligibility_results


def eligible() -> Eligibility:
    e = Eligibility()
    e.eligible = True
    e.household_value = 1
    return e


class FederalProgramsTestCase(TestCase):
    def setUp(self) -> None:
        self.federal = WhiteLabel.objects.create(name="Federal Programs", code=FEDERAL_WHITE_LABEL)
        self.co = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        self.wa = WhiteLabel.objects.create(name="Washington", code="wa", state_code="WA")
        self.category = ProgramCategory.objects.new_program_category(white_label=None, external_name="cash", icon="")
        self.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")

    def program(self, white_label: WhiteLabel, name: str, *, active: bool = True, **fields: Any) -> Program:
        program = Program.objects.new_program(white_label.code, name)
        program.active = active
        program.has_calculator = True
        program.category = self.category
        program.year = self.fpl_year
        for field, value in fields.items():
            setattr(program, field, value)
        program.save()
        return program

    def screen(self, white_label: WhiteLabel, **fields: Any) -> Screen:
        return Screen.objects.create(
            white_label=white_label, zipcode="80202", household_size=1, completed=False, **fields
        )

    def results(self, screen: Screen) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        with patch.object(Program, "eligibility", lambda *args: eligible()), patch(
            "screener.views.calc_pe_eligibility", return_value={"eligibility": {}, "_pe_data": {}}
        ):
            data, _, categories, _ = eligibility_results(screen)
        return data, categories


class TestResults(FederalProgramsTestCase):
    def test_a_federal_program_is_shown_to_every_white_label(self) -> None:
        federal = self.program(self.federal, "fed_account")
        self.program(self.co, "co_only")

        co_data, _ = self.results(self.screen(self.co))
        wa_data, _ = self.results(self.screen(self.wa))

        self.assertEqual(sorted(p["name_abbreviated"] for p in co_data), ["co_only", "fed_account"])
        self.assertEqual([p["program_id"] for p in wa_data], [federal.id])

    def test_it_lands_in_the_shared_category_alongside_state_programs(self) -> None:
        federal = self.program(self.federal, "fed_account")
        state = self.program(self.co, "co_only")

        _, categories = self.results(self.screen(self.co))

        self.assertEqual(len(categories), 1)
        self.assertEqual(sorted(categories[0]["programs"]), sorted([federal.id, state.id]))

    def test_programs_outside_calc_order_come_back_in_id_order(self) -> None:
        """The order the screener breaks value ties with; it must not depend on the query plan."""
        programs = [
            self.program(self.federal, "fed_b"),
            self.program(self.co, "co_a"),
            self.program(self.federal, "fed_a"),
            self.program(self.co, "co_b"),
        ]

        data, _ = self.results(self.screen(self.co))

        self.assertEqual([p["program_id"] for p in data], [p.id for p in programs])

    def test_an_inactive_federal_program_is_not_shown(self) -> None:
        self.program(self.federal, "fed_account", active=False)

        data, _ = self.results(self.screen(self.co))

        self.assertEqual(data, [])

    def test_without_federal_programs_results_are_unchanged(self) -> None:
        self.program(self.co, "co_only")
        self.program(self.wa, "wa_only")

        data, _ = self.results(self.screen(self.co))

        self.assertEqual([p["name_abbreviated"] for p in data], ["co_only"])

    def test_a_name_active_on_both_sides_shows_the_federal_row_once_and_logs(self) -> None:
        federal = self.program(self.federal, "shared_name")
        self.program(self.co, "shared_name")

        with self.assertLogs("programs.federal", level="ERROR") as logs:
            data, _ = self.results(self.screen(self.co))

        self.assertEqual([p["program_id"] for p in data], [federal.id])
        self.assertIn("shared_name", logs.output[0])

    def test_a_deactivated_state_row_loses_to_the_federal_row_silently(self) -> None:
        federal = self.program(self.federal, "shared_name")
        self.program(self.co, "shared_name", active=False)

        with self.assertNoLogs("programs.federal", level="ERROR"):
            data, _ = self.results(self.screen(self.co))

        self.assertEqual([p["program_id"] for p in data], [federal.id])

    def test_a_referrer_can_exclude_a_federal_program(self) -> None:
        federal = self.program(self.federal, "fed_account")
        referrer = Referrer.objects.create(white_label=self.co, referrer_code="partner", name="Partner")
        referrer.remove_programs.add(federal)

        data, _ = self.results(self.screen(self.co, referrer_code="partner"))

        self.assertEqual(data, [])

    def test_removing_a_state_program_also_removes_its_federal_replacement(self) -> None:
        self.program(self.federal, "shared_name")
        state = self.program(self.co, "shared_name", active=False)
        kept = self.program(self.co, "co_only")
        referrer = Referrer.objects.create(white_label=self.co, referrer_code="partner", name="Partner")
        referrer.remove_programs.add(state)

        data, _ = self.results(self.screen(self.co, referrer_code="partner"))

        self.assertEqual([p["program_id"] for p in data], [kept.id])


class TestCurrentBenefits(FederalProgramsTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = User.objects.create_user(email_or_cell="toggle@example.com", password="password")
        self.user.user_permissions.add(Permission.objects.get(codename="change_screen"))
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def benefits(self, screen: Screen) -> list[int]:
        return list(CurrentBenefit.objects.filter(screen=screen).values_list("program_id", flat=True))

    def test_the_toggle_resolves_a_federal_program(self) -> None:
        federal = self.program(self.federal, "fed_account")
        screen = self.screen(self.co)

        response = self.client.patch(
            f"/api/screens/{screen.uuid}/current-benefits/", {"name_abbreviated": "fed_account", "has": True}, "json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.benefits(screen), [federal.id])

    def test_the_toggle_picks_the_federal_row_over_a_deactivated_state_row(self) -> None:
        """Two rows with one name would raise MultipleObjectsReturned in a plain get()."""
        federal = self.program(self.federal, "shared_name")
        self.program(self.co, "shared_name", active=False)
        screen = self.screen(self.co)

        response = self.client.patch(
            f"/api/screens/{screen.uuid}/current-benefits/", {"name_abbreviated": "shared_name", "has": True}, "json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.benefits(screen), [federal.id])

    def test_before_the_move_the_toggle_keeps_the_live_state_row(self) -> None:
        """A federal row imported inactive ahead of the move must not capture the benefit."""
        self.program(self.federal, "shared_name", active=False)
        state = self.program(self.co, "shared_name")
        screen = self.screen(self.co)

        self.client.patch(
            f"/api/screens/{screen.uuid}/current-benefits/", {"name_abbreviated": "shared_name", "has": True}, "json"
        )

        self.assertEqual(self.benefits(screen), [state.id])

    def test_unticking_removes_the_state_row_a_screen_saved_before_the_move(self) -> None:
        """Screens saved before a program moved still point at the deactivated state row."""
        self.program(self.federal, "shared_name")
        state = self.program(self.co, "shared_name", active=False)
        screen = self.screen(self.co)
        CurrentBenefit.objects.create(screen=screen, program=state)

        response = self.client.patch(
            f"/api/screens/{screen.uuid}/current-benefits/", {"name_abbreviated": "shared_name", "has": False}, "json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"current_benefits": []})
        self.assertEqual(self.benefits(screen), [])
        self.assertFalse(Screen.objects.get(pk=screen.pk).has_benefit("shared_name"))

    def test_ticking_moves_that_screen_onto_the_federal_row_without_a_second_row(self) -> None:
        federal = self.program(self.federal, "shared_name")
        state = self.program(self.co, "shared_name", active=False)
        screen = self.screen(self.co)
        CurrentBenefit.objects.create(screen=screen, program=state)

        response = self.client.patch(
            f"/api/screens/{screen.uuid}/current-benefits/", {"name_abbreviated": "shared_name", "has": True}, "json"
        )

        self.assertEqual(response.data, {"current_benefits": ["shared_name"]})
        self.assertEqual(self.benefits(screen), [federal.id])

    def test_unticking_leaves_other_benefits_alone(self) -> None:
        self.program(self.federal, "shared_name")
        other = self.program(self.co, "co_only")
        screen = self.screen(self.co)
        CurrentBenefit.objects.create(screen=screen, program=other)

        self.client.patch(
            f"/api/screens/{screen.uuid}/current-benefits/", {"name_abbreviated": "shared_name", "has": False}, "json"
        )

        self.assertEqual(self.benefits(screen), [other.id])

    def test_the_toggle_still_404s_an_unknown_name(self) -> None:
        screen = self.screen(self.co)

        response = self.client.patch(
            f"/api/screens/{screen.uuid}/current-benefits/", {"name_abbreviated": "nope", "has": True}, "json"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "No program 'nope' is offered to white label 'co'.")

    def test_the_screen_write_path_keeps_a_federal_benefit(self) -> None:
        federal = self.program(self.federal, "shared_name")
        self.program(self.co, "shared_name", active=False)
        state = self.program(self.co, "co_only")
        screen = self.screen(self.co)

        _write_current_benefits(screen, ["shared_name", "co_only"])

        self.assertEqual(sorted(self.benefits(screen)), sorted([federal.id, state.id]))
        self.assertTrue(screen.has_benefit("shared_name"))

    def ssi_screen(self, white_label: WhiteLabel) -> Screen:
        screen = self.screen(white_label)
        add_income(add_member(screen), 900, income_type="sSI")
        return screen

    def test_ssi_income_derives_a_live_federal_ssi_program(self) -> None:
        self.program(self.federal, "ssi", base_program="ssi")

        self.assertEqual(_derived_current_benefit_names(self.ssi_screen(self.wa)), {"ssi"})

    def test_ssi_income_ignores_a_federal_ssi_program_not_launched_yet(self) -> None:
        self.program(self.federal, "ssi", active=False, base_program="ssi")
        self.program(self.co, "co_ssi", active=False, base_program="ssi")

        # The inactive state row is still derived, as before federal programs existed.
        self.assertEqual(_derived_current_benefit_names(self.ssi_screen(self.co)), {"co_ssi"})
        self.assertEqual(_derived_current_benefit_names(self.ssi_screen(self.wa)), set())


class TestScreenerOptions(FederalProgramsTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(user=User.objects.create_user(email_or_cell="o@example.com", password="pw"))

    def test_the_has_benefits_step_lists_federal_programs(self) -> None:
        self.program(self.federal, "fed_account", show_in_has_benefits_step=True)
        self.program(self.co, "co_only", show_in_has_benefits_step=True)
        self.program(self.wa, "wa_only", show_in_has_benefits_step=True)

        response = self.client.get("/api/screener-options/co/has-benefits-programs/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(p["name_abbreviated"] for p in response.data), ["co_only", "fed_account"])

    def test_the_current_benefits_page_includes_federal_programs(self) -> None:
        federal = self.program(self.federal, "fed_account", show_on_current_benefits=True)
        state = self.program(self.co, "co_only", show_on_current_benefits=True)
        self.program(self.wa, "wa_only", show_on_current_benefits=True)

        data = ProgramCategorySerializer(self.category, context={"white_label": "co"}).data

        self.assertEqual(sorted(p["id"] for p in data["programs"]), sorted([federal.id, state.id]))

    def test_the_current_benefits_program_list_shows_a_shared_name_once(self) -> None:
        """Even with both rows active (an unfinished move), the list carries the federal row only."""
        federal = self.program(self.federal, "shared_name", show_on_current_benefits=True)
        self.program(self.co, "shared_name", show_on_current_benefits=True)
        state = self.program(self.co, "co_only", show_on_current_benefits=True)

        with self.assertLogs("programs.federal", level="ERROR"):
            response = self.client.get("/api/programs/co/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(p["id"] for p in response.data), sorted([federal.id, state.id]))

    def test_federal_is_not_a_state_option(self) -> None:
        self.assertNotIn(FEDERAL_WHITE_LABEL, [option["code"] for option in state_options()])


class TestScreensUnderFederal(FederalProgramsTestCase):
    """No screener serves `federal`, so only test screens may be saved under it.

    A test screen there sees the federal programs alone, with no location, which is how a
    federal program's API tests run.
    """

    BODY = {"household_members": [], "expenses": [], "current_benefits": []}

    def post(self, body: dict[str, Any]) -> Any:
        user = User.objects.create_user(email_or_cell="create@example.com", password="pw")
        user.user_permissions.add(Permission.objects.get(codename="add_screen"))
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post("/api/screens/", body, format="json")

    def test_a_real_screen_under_federal_is_rejected(self) -> None:
        response = self.post({**self.BODY, "white_label": FEDERAL_WHITE_LABEL})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["white_label"], ["'federal' only takes test screens: send \"is_test\": true."])
        self.assertFalse(Screen.objects.filter(white_label=self.federal).exists())

    def test_a_test_screen_under_federal_is_saved_without_a_location(self) -> None:
        response = self.post({**self.BODY, "white_label": FEDERAL_WHITE_LABEL, "is_test": True})

        self.assertEqual(response.status_code, 201, response.data)
        screen = Screen.objects.get(white_label=self.federal)
        self.assertIsNone(screen.zipcode)
        self.assertTrue(screen.is_test_data)

    def test_a_test_screen_under_federal_sees_only_federal_programs(self) -> None:
        federal = self.program(self.federal, "fed_account")
        self.program(self.co, "co_only")

        data, _ = self.results(self.screen(self.federal, is_test=True))

        self.assertEqual([p["program_id"] for p in data], [federal.id])

    def test_moving_a_real_screen_to_federal_is_rejected(self) -> None:
        screen = self.screen(self.co)

        serializer = ScreenSerializer(screen, data={**self.BODY, "white_label": FEDERAL_WHITE_LABEL})

        self.assertFalse(serializer.is_valid())
        self.assertIn("white_label", serializer.errors)


class TestResultsUnchangedWithoutActiveFederalPrograms(FederalProgramsTestCase):
    """Until a program moves, the federal union must change nothing a screen gets back.

    For each kind of white label, including the ones with no state (`co_tax_calculator`,
    `_default`) or a shared state (`cesn`), the full `eligibility_results` output is captured
    with no federal white label at all, then again once it exists holding only inactive
    programs (one reusing a state program's name), and the two serialized forms must match
    exactly.
    """

    WHITE_LABELS = {"co": "CO", "cesn": "CO", "co_tax_calculator": None, "_default": None}

    def setUp(self) -> None:
        super().setUp()
        # The base fixture creates `federal`; this test needs the world from before it existed.
        self.federal.delete()

    def snapshot(self, screen: Screen) -> str:
        """Every output of a fresh results run, serialized; the screen's snapshots are cleared
        first so the `new` flag doesn't depend on an earlier run."""
        EligibilitySnapshot.objects.filter(screen=screen).delete()
        with patch.object(Program, "eligibility", lambda *args: eligible()), patch(
            "screener.views.calc_pe_eligibility", return_value={"eligibility": {}, "_pe_data": {}}
        ):
            output = eligibility_results(screen)
        return json.dumps(output, sort_keys=True, default=str)

    def test_every_kind_of_white_label_gets_identical_results(self) -> None:
        screens = {}
        for code, state_code in self.WHITE_LABELS.items():
            white_label = WhiteLabel.objects.filter(code=code).first() or WhiteLabel.objects.create(
                name=code, code=code, state_code=state_code
            )
            self.program(white_label, f"{code}_benefit")
            self.program(white_label, "shared_name")
            self.program(white_label, f"{code}_retired", active=False)
            screens[code] = self.screen(white_label)

        before = {code: self.snapshot(screen) for code, screen in screens.items()}

        federal = WhiteLabel.objects.create(name="Federal Programs", code=FEDERAL_WHITE_LABEL)
        self.program(federal, "shared_name", active=False)
        self.program(federal, "fed_only", active=False)

        for code, screen in screens.items():
            with self.subTest(white_label=code):
                self.assertEqual(self.snapshot(screen), before[code])


class _Superuser:
    is_superuser = True
    is_active = True
    is_staff = True

    def has_perm(self, perm: str, obj: Optional[object] = None) -> bool:
        return True


class TestAdminPickers(FederalProgramsTestCase):
    """A white label's rows may reference a federal program, but not attach content to one."""

    def form(self, model_admin: ModelAdmin, obj: Model) -> type[ModelForm]:
        request = RequestFactory().get("/admin/")
        request.user = _Superuser()
        return model_admin.get_form(request, obj=obj)

    def test_a_referrer_can_pick_a_federal_program_to_remove(self) -> None:
        federal = self.program(self.federal, "fed_account")
        own = self.program(self.co, "co_only")
        other = self.program(self.wa, "wa_only")
        referrer = Referrer.objects.create(white_label=self.co, referrer_code="partner", name="Partner")

        choices = set(self.form(ReferrerAdmin(Referrer, AdminSite()), referrer).base_fields["remove_programs"].queryset)

        self.assertEqual(choices, {federal, own})
        self.assertNotIn(other, choices)

    def test_a_state_warning_cannot_be_attached_to_a_federal_program(self) -> None:
        federal = self.program(self.federal, "fed_account")
        own = self.program(self.co, "co_only")
        warning = WarningMessage.objects.new_warning("co", "_show")

        choices = set(
            self.form(WarningMessageAdmin(WarningMessage, AdminSite()), warning).base_fields["programs"].queryset
        )

        self.assertIn(own, choices)
        self.assertNotIn(federal, choices)


class ProgramAdminTestCase(FederalProgramsTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.model_admin = ProgramAdmin(Program, AdminSite())
        self.request = RequestFactory().post("/admin/")
        self.request.user = _Superuser()

    def bound_form(self, program: Program, **changes: Any) -> ModelForm:
        form_class = self.model_admin.get_form(self.request, obj=program)
        data = {
            name: value
            for name, value in model_to_dict(program, fields=list(form_class.base_fields)).items()
            if value is not None
        }
        data = {name: [v.pk for v in value] if isinstance(value, list) else value for name, value in data.items()}
        data.update(changes)
        data = {name: value for name, value in data.items() if value is not False}
        return form_class(data=data, instance=program)


class TestFederalDeactivationInAdmin(ProgramAdminTestCase):
    """Switching off a federal program hides it everywhere, so the admin makes that deliberate."""

    def test_switching_off_a_federal_program_needs_confirmation(self) -> None:
        federal = self.program(self.federal, "fed_account")

        form = self.bound_form(federal, active=False)

        self.assertFalse(form.is_valid())
        self.assertIn("every white label", form.errors["confirm_federal_deactivation"][0])

    def test_a_confirmed_switch_off_saves_with_a_warning(self) -> None:
        federal = self.program(self.federal, "fed_account")
        self.program(self.co, "fed_account", active=False)
        form = self.bound_form(federal, active=False, confirm_federal_deactivation=True)
        self.assertTrue(form.is_valid(), form.errors)

        with patch("programs.admin.messages.warning") as warning:
            self.model_admin.save_model(self.request, form.save(commit=False), form, change=True)

        federal.refresh_from_db()
        self.assertFalse(federal.active)
        message = warning.call_args.args[1]
        self.assertIn("hidden from every white label", message)
        self.assertIn("No state version replaces it", message)

    def test_the_warning_names_state_versions_that_are_still_active(self) -> None:
        federal = self.program(self.federal, "fed_account")
        self.program(self.wa, "fed_account")
        form = self.bound_form(federal, active=False, confirm_federal_deactivation=True)
        self.assertTrue(form.is_valid(), form.errors)

        with patch("programs.admin.messages.warning") as warning:
            self.model_admin.save_model(self.request, form.save(commit=False), form, change=True)

        self.assertIn("state versions under wa", warning.call_args.args[1])

    def test_moving_a_federal_program_to_a_state_while_switching_it_off_still_warns(self) -> None:
        federal = self.program(self.federal, "fed_account")
        form = self.bound_form(federal, white_label=self.co.pk, active=False, confirm_federal_deactivation=True)
        self.assertTrue(form.is_valid(), form.errors)

        with patch("programs.admin.messages.warning") as warning:
            self.model_admin.save_model(self.request, form.save(commit=False), form, change=True)

        self.assertIn("hidden from every white label", warning.call_args.args[1])

    def test_moving_a_state_program_to_federal_while_switching_it_off_does_not_warn(self) -> None:
        state = self.program(self.co, "co_only")
        form = self.bound_form(state, white_label=self.federal.pk, active=False)
        self.assertTrue(form.is_valid(), form.errors)

        with patch("programs.admin.messages.warning") as warning:
            self.model_admin.save_model(self.request, form.save(commit=False), form, change=True)

        warning.assert_not_called()

    def test_other_edits_to_a_federal_program_need_no_confirmation(self) -> None:
        federal = self.program(self.federal, "fed_account")

        form = self.bound_form(federal, low_confidence=True)

        self.assertTrue(form.is_valid(), form.errors)
        with patch("programs.admin.messages.warning") as warning:
            self.model_admin.save_model(self.request, form.save(commit=False), form, change=True)
        warning.assert_not_called()

    def test_a_state_program_switches_off_as_before(self) -> None:
        state = self.program(self.co, "co_only")

        form = self.bound_form(state, active=False)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("confirm_federal_deactivation", self.model_admin.get_fields(self.request, state))

    def test_the_list_page_locks_active_only_on_active_federal_programs(self) -> None:
        form_class = self.model_admin.get_changelist_form(self.request)

        def locked(program: Program) -> bool:
            return form_class(instance=program).fields["active"].disabled

        self.assertTrue(locked(self.program(self.federal, "fed_on")))
        self.assertFalse(locked(self.program(self.federal, "fed_off", active=False)))
        self.assertFalse(locked(self.program(self.co, "co_only")))


class TestFederalStateVersionsInAdmin(ProgramAdminTestCase):
    """A federal program's edit form lists the state versions sharing its name."""

    def test_programs_switch_on_without_a_duplicate_check(self) -> None:
        self.assertTrue(self.bound_form(self.program(self.co, "co_only", active=False), active=True).is_valid())
        self.assertTrue(self.bound_form(self.program(self.federal, "fed_only", active=False), active=True).is_valid())

    def test_a_federal_program_lists_its_state_versions(self) -> None:
        federal = self.program(self.federal, "fed_account", active=False)
        co = self.program(self.co, "fed_account")
        self.program(self.wa, "fed_account", active=False)

        shown = self.model_admin.state_versions(federal)

        self.assertIn(f'/admin/programs/program/{co.pk}/change/">co (active)</a>', shown)
        self.assertIn("wa (inactive)", shown)
        self.assertIn("state_versions", self.model_admin.get_fields(self.request, federal))
        self.assertNotIn("state_versions", self.model_admin.get_fields(self.request, co))
