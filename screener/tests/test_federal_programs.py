"""Programs under the `federal` white label are shown to every white label.

A federal row reuses its calculator's `name_abbreviated`, the same name the state rows it
replaces carry, and moving a program deactivates those state rows. These tests cover the
read paths that union federal programs in (results, current benefits, the has-benefits step,
the current-benefits page), the collision rule when a name is still active on both sides
(log and prefer the federal row, never raise), and the two hard failures that keep that from
happening: the import guard and `audit_federal_programs`.

Calculators are stubbed through `Program.eligibility`: what is under test is which rows the
results page fetches and publishes, not any program's rule.
"""

import json
from typing import Any, Optional
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Model
from django.forms import ModelForm
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from authentication.models import User
from configuration.white_labels import state_options
from programs.federal import FEDERAL_WHITE_LABEL
from programs.framework.base import Eligibility
from programs.admin import ReferrerAdmin, WarningMessageAdmin
from programs.models import FederalPoveryLimit, Program, ProgramCategory, Referrer, WarningMessage
from programs.serializers import ProgramCategorySerializer
from screener.models import CurrentBenefit, EligibilitySnapshot, Screen, WhiteLabel
from screener.serializers import ScreenSerializer, _write_current_benefits
from screener.views import eligibility_results

CONFIG_DIR = (
    Path(__file__).resolve().parents[2] / "programs" / "management" / "commands" / "import_program_config_data" / "data"
)


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


class TestNoScreensUnderFederal(FederalProgramsTestCase):
    """No screener serves `federal`, so no screen may be saved under it, by the API or otherwise."""

    BODY = {"household_members": [], "expenses": [], "current_benefits": []}

    def test_creating_a_screen_under_federal_is_rejected(self) -> None:
        user = User.objects.create_user(email_or_cell="create@example.com", password="pw")
        user.user_permissions.add(Permission.objects.get(codename="add_screen"))
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post("/api/screens/", {**self.BODY, "white_label": FEDERAL_WHITE_LABEL}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["white_label"], ["'federal' is not a screener white label."])
        self.assertFalse(Screen.objects.filter(white_label=self.federal).exists())

    def test_moving_a_screen_to_federal_is_rejected(self) -> None:
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


class TestAudit(FederalProgramsTestCase):
    def test_clean_when_no_name_is_active_on_both_sides(self) -> None:
        self.program(self.federal, "shared_name")
        self.program(self.co, "shared_name", active=False)
        out = StringIO()

        call_command("audit_federal_programs", stdout=out)

        self.assertIn("No program is active", out.getvalue())

    def test_fails_on_a_name_active_on_both_sides(self) -> None:
        self.program(self.federal, "shared_name")
        self.program(self.co, "shared_name")
        self.program(self.wa, "shared_name")

        with self.assertRaisesMessage(CommandError, "shared_name: federal and co, wa"):
            call_command("audit_federal_programs", stdout=StringIO())


class TestImportGuard(FederalProgramsTestCase):
    def setUp(self) -> None:
        super().setUp()
        translate = patch("programs.management.commands.import_program_config.Translate")
        translate.start().return_value.bulk_translate.side_effect = lambda langs, texts: {
            text: {lang: text for lang in langs} for text in texts
        }
        self.addCleanup(translate.stop)

    def import_config(self, white_label_code: str, name: str, active: bool) -> None:
        config = {
            "white_label": {"code": white_label_code},
            "program_category": {"external_name": "cash"},
            "program": {"name_abbreviated": name, "name": "Test", "active": active},
        }
        path = Path(self.enterContext(tempfile.TemporaryDirectory())) / "config.json"
        path.write_text(json.dumps(config))
        call_command("import_program_config", str(path), stdout=StringIO())

    def test_refuses_an_active_federal_import_over_an_active_state_row(self) -> None:
        self.program(self.co, "shared_name")

        with self.assertRaisesMessage(CommandError, "already active under co"):
            self.import_config(FEDERAL_WHITE_LABEL, "shared_name", active=True)

        self.assertFalse(Program.objects.filter(white_label=self.federal).exists())

    def test_refuses_an_active_state_import_over_an_active_federal_row(self) -> None:
        self.program(self.federal, "shared_name")

        with self.assertRaisesMessage(CommandError, "already active under federal"):
            self.import_config("wa", "shared_name", active=True)

    def test_allows_it_once_the_state_row_is_inactive(self) -> None:
        self.program(self.co, "shared_name", active=False)

        self.import_config(FEDERAL_WHITE_LABEL, "shared_name", active=True)

        self.assertTrue(Program.objects.filter(white_label=self.federal, name_abbreviated="shared_name").exists())

    def test_allows_an_inactive_import(self) -> None:
        self.program(self.co, "shared_name")

        self.import_config(FEDERAL_WHITE_LABEL, "shared_name", active=False)

        self.assertFalse(Program.objects.get(white_label=self.federal).active)


class TestConfigFiles(TestCase):
    """PR CI's database is empty, so the database audit can't run there; the committed
    configs are what a reviewer can still catch a duplicate in."""

    def test_no_active_federal_config_shares_a_name_with_an_active_state_config(self) -> None:
        active: dict[str, set[str]] = {}
        for path in CONFIG_DIR.glob("*.json"):
            config = json.loads(path.read_text())
            if not config.get("program", {}).get("active"):
                continue
            name = config["program"]["name_abbreviated"]
            active.setdefault(name, set()).add(config["white_label"]["code"])

        duplicates = {
            name: sorted(codes - {FEDERAL_WHITE_LABEL})
            for name, codes in active.items()
            if FEDERAL_WHITE_LABEL in codes and len(codes) > 1
        }
        self.assertEqual(duplicates, {}, "Deactivate (or delete) the state configs a federal config replaces.")


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
