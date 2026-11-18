"""
`apply_program` writes one program's payload: the program row and its English text always match
the payload, navigators, documents and warnings are created only when missing, and nothing is
ever unlinked.
"""

import copy
import io
import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from programs.management.commands._program_payload import PayloadError, parse_payload
from programs.management.commands._program_record_sync import validate_record
from programs.models import (
    Document,
    FederalPoveryLimit,
    LegalStatus,
    Navigator,
    Program,
    ProgramCategory,
    ProgramImportLog,
    ProgramNavigator,
    WarningMessage,
)
from screener.models import WhiteLabel
from translations.models import Translation

FIXTURE = Path(__file__).parent / "fixtures" / "example_program_payload.json"
PROGRAM = "co_example_program"
NAV = f"{PROGRAM}_nav"
DOC = f"{PROGRAM}_id"
WARNING = f"{PROGRAM}_waitlist"


def example_payload() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def fake_translate(langs: list[str], texts: list[str], strict: bool = True) -> dict[str, dict[str, str]]:
    return {text: {lang: f"[{lang}] {text}" for lang in langs} for text in texts}


class ExamplePayloadTests(SimpleTestCase):
    """The shared example is the contract with program-ops' renderer, which tests the same file."""

    def test_the_example_payload_parses(self) -> None:
        payload = parse_payload(example_payload())

        self.assertEqual(payload.white_label, "co")
        self.assertEqual(payload.program.name_abbreviated, PROGRAM)
        self.assertEqual([seed.external_name for seed in payload.navigators], [NAV])

    def test_the_example_payload_is_also_a_valid_program_record(self) -> None:
        self.assertEqual(validate_record(parse_payload(example_payload()).as_record()), [])


class PayloadValidationTests(SimpleTestCase):
    def problems(self, payload: dict[str, Any]) -> list[str]:
        with self.assertRaises(PayloadError) as raised:
            parse_payload(payload)
        return raised.exception.problems

    def test_a_missing_program_field_is_named(self) -> None:
        payload = example_payload()
        del payload["program"]["estimated_value"]
        del payload["program"]["low_confidence"]

        self.assertEqual(self.problems(payload), ["program is missing low_confidence, estimated_value"])

    def test_wrong_types_are_named(self) -> None:
        payload = example_payload()
        payload["program"]["has_calculator"] = "yes"
        payload["program"]["description"] = None
        payload["program"]["legal_status_required"] = "citizen"
        payload["program"]["year"] = 2025

        problems = self.problems(payload)

        self.assertIn("program.has_calculator must be true or false", problems)
        self.assertIn("program.description must be a string", problems)
        self.assertIn("program.legal_status_required must be a list of strings", problems)
        self.assertIn('program.year must be a string, such as "2025", or null', problems)

    def test_a_bad_url_is_named(self) -> None:
        payload = example_payload()
        payload["program"]["apply_button_link"] = "example.org/apply"
        payload["navigators"][0]["assistance_link"] = "[Help](https://example.org/help)"

        problems = self.problems(payload)

        self.assertIn("program.apply_button_link 'example.org/apply' isn't an http(s) URL", problems)
        self.assertIn(
            f"navigators[0] ({NAV}): assistance_link '[Help](https://example.org/help)' isn't an http(s) URL", problems
        )

    def test_a_link_urlparse_cant_read_is_reported_with_the_others(self) -> None:
        payload = example_payload()
        payload["program"]["learn_more_link"] = "http://[invalid"
        payload["program"]["has_calculator"] = "yes"

        problems = self.problems(payload)

        self.assertIn("program.learn_more_link 'http://[invalid' isn't an http(s) URL", problems)
        self.assertIn("program.has_calculator must be true or false", problems)

    def test_a_program_key_that_isnt_lowercase_is_refused(self) -> None:
        payload = example_payload()
        payload["program"]["name_abbreviated"] = "CO_Example_Program"

        self.assertIn("program.name_abbreviated 'CO_Example_Program' must be lowercase", self.problems(payload))

    def test_an_empty_link_is_allowed(self) -> None:
        payload = example_payload()
        payload["program"]["learn_more_link"] = ""

        self.assertEqual(parse_payload(payload).program.text["learn_more_link"], "")

    def test_active_and_unknown_keys_fail(self) -> None:
        payload = example_payload()
        payload["program"]["active"] = True
        payload["program"]["has_calculcator"] = True
        payload["extra"] = {}

        problems = self.problems(payload)

        self.assertIn("program.active isn't a payload field: a program is switched on or off in the admin", problems)
        self.assertIn("unknown program key 'has_calculcator'", problems)
        self.assertIn("unknown top-level key 'extra'", problems)

    def test_the_singular_warning_message_is_refused(self) -> None:
        payload = example_payload()
        payload["warning_message"] = payload.pop("warning_messages")[0]

        self.assertIn("use 'warning_messages' (a list), not 'warning_message'", self.problems(payload))

    def test_a_partial_entry_is_named(self) -> None:
        payload = example_payload()
        payload["navigators"][0] = {"external_name": NAV, "description": "Only a description"}

        problems = self.problems(payload)

        self.assertTrue(
            any(problem.startswith(f"navigators[0] ({NAV}) is missing name, email") for problem in problems)
        )

    def test_an_unknown_legal_status_is_named(self) -> None:
        payload = example_payload()
        payload["program"]["legal_status_required"] = ["citizen", "gc_under5"]

        problems = self.problems(payload)

        self.assertTrue(
            any(
                p.startswith("program.legal_status_required has values the screener doesn't know: gc_under5")
                for p in problems
            )
        )

    def test_an_unknown_navigator_language_is_named(self) -> None:
        payload = example_payload()
        payload["navigators"][0]["languages"] = ["English"]

        problems = self.problems(payload)

        self.assertTrue(any("languages has values the screener doesn't know: English" in p for p in problems))

    def test_an_unknown_warning_legal_status_and_calculator_are_named(self) -> None:
        payload = example_payload()
        payload["warning_messages"][0]["legal_statuses"] = ["other"]
        payload["warning_messages"][0]["calculator"] = "co_old_name"

        problems = self.problems(payload)

        self.assertTrue(any("legal_statuses has values the screener doesn't know: other" in p for p in problems))
        self.assertIn(
            f"warning_messages[0] ({WARNING}): calculator 'co_old_name' isn't a registered warning calculator", problems
        )

    def test_an_unknown_value_format_is_named(self) -> None:
        payload = example_payload()
        payload["program"]["value_format"] = "monthly"

        self.assertEqual(
            self.problems(payload), ["program.value_format must be one of null, lump_sum, estimated_annual"]
        )


class ApplyProgramBase(TestCase):
    def setUp(self) -> None:
        self.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        WhiteLabel.objects.create(name="Federal", code="federal")
        for status in ("citizen", "refugee"):
            LegalStatus.objects.create(status=status)
        for year in ("2025", "2026"):
            FederalPoveryLimit.objects.create(year=year, period=year)
        ProgramCategory.objects.new_program_category(None, "food", "food")

        calculators = patch(
            "programs.management.commands.apply_program.all_calculator_classes",
            return_value={PROGRAM: MagicMock()},
        )
        calculators.start()
        self.addCleanup(calculators.stop)

        translate = patch("programs.management.commands._program_record_sync.Translate")
        mock = translate.start()
        mock.return_value.bulk_translate.side_effect = fake_translate
        mock.languages = ["es", "vi"]
        self.addCleanup(translate.stop)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.payload = example_payload()

    def apply(self, payload: dict[str, Any], *args: str) -> str:
        path = Path(self.temp_dir.name) / "payload.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        out = io.StringIO()
        call_command("apply_program", "--file", str(path), *args, stdout=out)
        return out.getvalue()

    def program(self) -> Program:
        return Program.objects.get(white_label=self.white_label, name_abbreviated=PROGRAM)

    def navigator_names(self) -> list[str]:
        return list(
            ProgramNavigator.objects.filter(program=self.program())
            .order_by("order", "id")
            .values_list("navigator__external_name", flat=True)
        )


class CreateTests(ApplyProgramBase):
    def test_a_new_program_is_created_switched_off_with_every_field(self) -> None:
        output = self.apply(self.payload)

        program = self.program()
        self.assertFalse(program.active)
        self.assertEqual(program.name.get_lang("en-us").text, "Example Food Program")
        self.assertEqual(program.estimated_decision_time.get_lang("en-us").text, "30 days")
        self.assertEqual(program.year.year, "2025")
        self.assertEqual(program.category.external_name, "food")
        self.assertEqual(list(program.legal_status_required.values_list("status", flat=True)), ["citizen"])
        self.assertTrue(program.show_on_current_benefits)
        self.assertIn("New program, created switched off.", output)

    def test_new_shared_rows_are_created_and_linked(self) -> None:
        self.apply(self.payload)

        program = self.program()
        navigator = Navigator.objects.get(external_name=NAV)
        self.assertEqual(navigator.name.get_lang("en-us").text, "Example Help Desk")
        self.assertEqual(str(navigator.phone_number), "+13035550100")
        self.assertEqual(self.navigator_names(), [NAV])
        self.assertEqual(program.documents.get().text.get_lang("en-us").text, "A photo ID")
        self.assertEqual(program.warning_messages.get().message.get_lang("en-us").text, "There is a waitlist.")

    def test_reapplying_the_same_payload_changes_nothing(self) -> None:
        self.apply(self.payload)

        output = self.apply(self.payload)

        self.assertIn("✓ Matches the payload.", output)
        self.assertEqual(ProgramImportLog.objects.order_by("applied_at").last().changes, [])

    def test_a_program_without_a_registered_calculator_is_not_created(self) -> None:
        self.payload["program"]["name_abbreviated"] = "co_not_built_yet"

        with self.assertRaisesMessage(CommandError, "has no registered calculator yet"):
            self.apply(self.payload)

        self.assertFalse(Program.objects.filter(name_abbreviated="co_not_built_yet").exists())
        self.assertFalse(ProgramImportLog.objects.exists())

    def test_a_tracking_only_program_doesnt_wait_for_a_calculator(self) -> None:
        self.payload["program"]["name_abbreviated"] = "co_tracking_only"
        self.payload["program"]["has_calculator"] = False

        self.apply(self.payload)

        self.assertTrue(Program.objects.filter(name_abbreviated="co_tracking_only").exists())

    def test_a_malformed_payload_writes_nothing(self) -> None:
        self.payload["program"]["show_on_current_benefits"] = "true"

        with self.assertRaisesMessage(CommandError, "program.show_on_current_benefits must be true or false"):
            self.apply(self.payload)

        self.assertFalse(Program.objects.exists())
        self.assertFalse(Navigator.objects.exists())

    def test_a_failed_write_rolls_back_the_whole_apply(self) -> None:
        self.payload["program"]["required_programs"] = ["co_no_such_program"]

        with self.assertRaisesMessage(CommandError, "no program 'co_no_such_program' in 'co' or 'federal'"):
            self.apply(self.payload)

        self.assertFalse(Program.objects.exists())
        self.assertFalse(Navigator.objects.exists())
        self.assertFalse(ProgramImportLog.objects.exists())

    def test_a_reference_to_a_missing_row_fails(self) -> None:
        self.payload["documents"] = [{"external_name": "no_such_document"}]

        with self.assertRaisesMessage(CommandError, "document 'no_such_document' doesn't exist"):
            self.apply(self.payload)

        self.assertFalse(Program.objects.exists())


class FederalReferenceTests(ApplyProgramBase):
    """A federal payload referencing a state's navigator or warning links it and notes which state sees it."""

    def setUp(self) -> None:
        super().setUp()
        self.payload["white_label"]["code"] = "federal"
        self.state_nav = Navigator.objects.new_navigator(white_label="co", name="co_clinics")
        self.state_nav.external_name = "co_clinics"
        self.state_nav.save()
        self.state_warning = WarningMessage.objects.new_warning("co", "_show", "co_notice")
        self.payload["navigators"].append({"external_name": "co_clinics"})
        self.payload["warning_messages"].append({"external_name": "co_notice"})

    def federal_program(self) -> Program:
        return Program.objects.get(white_label__code="federal", name_abbreviated=PROGRAM)

    def test_state_rows_are_linked_and_stay_on_their_state(self) -> None:
        self.apply(self.payload)

        program = self.federal_program()
        self.assertTrue(ProgramNavigator.objects.filter(program=program, navigator=self.state_nav).exists())
        self.assertIn(program, self.state_warning.programs.all())
        self.state_nav.refresh_from_db()
        self.state_warning.refresh_from_db()
        self.assertEqual(self.state_nav.white_label.code, "co")
        self.assertEqual(self.state_warning.white_label.code, "co")

    def test_each_state_row_gets_a_note_without_advice_to_move_it(self) -> None:
        output = self.apply(self.payload)

        for kind, name in (("navigator", "co_clinics"), ("warning", "co_notice")):
            self.assertIn(
                f"{kind} '{name}' is on the 'co' white label, so on this federal program only screens in the same "
                "state as 'co' see it.",
                output,
            )
        self.assertNotIn("moves it to 'federal'", output)

    def test_a_federal_row_gets_no_note(self) -> None:
        federal = WhiteLabel.objects.get(code="federal")
        Navigator.objects.filter(pk=self.state_nav.pk).update(white_label=federal)
        WarningMessage.objects.filter(pk=self.state_warning.pk).update(white_label=federal)

        output = self.apply(self.payload)

        self.assertNotIn("so on this federal program only", output)


class UpdateTests(ApplyProgramBase):
    def setUp(self) -> None:
        super().setUp()
        self.apply(self.payload)

    def test_program_fields_always_match_the_payload(self) -> None:
        program = self.program()
        program.low_confidence = True
        program.save()
        Translation.objects.edit_translation_by_id(program.name.id, "en-us", "Renamed in the admin", manual=True)

        self.apply(self.payload)

        program.refresh_from_db()
        self.assertFalse(program.low_confidence)
        self.assertEqual(program.name.get_lang("en-us").text, "Example Food Program")

    def test_a_changed_description_is_written_and_retranslated_keeping_hand_edits(self) -> None:
        description = self.program().description
        Translation.objects.edit_translation_by_id(description.id, "es", "Traducción a mano", manual=True)
        updated = copy.deepcopy(self.payload)
        updated["program"]["description"] = "Monthly help buying groceries and household items."

        output = self.apply(updated)

        description.refresh_from_db()
        self.assertEqual(description.get_lang("en-us").text, "Monthly help buying groceries and household items.")
        self.assertEqual(description.get_lang("vi").text, "[vi] Monthly help buying groceries and household items.")
        self.assertEqual(description.get_lang("es").text, "Traducción a mano")
        self.assertIn("hand-edited translations are kept (es)", output)

    def test_an_existing_shared_row_is_linked_and_left_as_it_is(self) -> None:
        navigator = Navigator.objects.get(external_name=NAV)
        Translation.objects.edit_translation_by_id(navigator.name.id, "en-us", "Renamed in the admin", manual=True)
        navigator.phone_number = "+13035550199"
        navigator.save()
        ProgramNavigator.objects.filter(program=self.program()).delete()

        output = self.apply(self.payload)

        navigator.refresh_from_db()
        self.assertEqual(navigator.name.get_lang("en-us").text, "Renamed in the admin")
        self.assertEqual(str(navigator.phone_number), "+13035550199")
        self.assertEqual(self.navigator_names(), [NAV])
        self.assertIn(
            f"navigator '{NAV}' already exists, so it was left as it is. It differs from the payload in: name, "
            f"phone_number.",
            output,
        )

    def test_an_existing_row_made_elsewhere_is_linked_without_edits(self) -> None:
        document = Document.objects.new_document(white_label="co", external_name="shared_proof_of_income")
        Translation.objects.edit_translation_by_id(document.text.id, "en-us", "Pay stubs", manual=True)
        updated = copy.deepcopy(self.payload)
        updated["documents"].append({"external_name": "shared_proof_of_income", "text": "Proof of income"})

        self.apply(updated)

        document.refresh_from_db()
        self.assertEqual(document.text.get_lang("en-us").text, "Pay stubs")
        self.assertIn(document, self.program().documents.all())

    def test_nothing_is_ever_unlinked(self) -> None:
        extra = Navigator.objects.new_navigator(white_label="co", name="Linked in the admin")
        extra.external_name = "linked_in_the_admin"
        extra.save()
        ProgramNavigator.objects.create(program=self.program(), navigator=extra, order=5)
        updated = copy.deepcopy(self.payload)
        updated["documents"] = []
        updated["warning_messages"] = []

        self.apply(updated)

        program = self.program()
        self.assertEqual(self.navigator_names(), [NAV, "linked_in_the_admin"])
        self.assertTrue(program.documents.filter(external_name=DOC).exists())
        self.assertTrue(WarningMessage.objects.get(external_name=WARNING).programs.filter(id=program.id).exists())

    def test_navigator_order_set_in_the_admin_is_kept(self) -> None:
        first = Navigator.objects.new_navigator(white_label="co", name="First in the admin")
        first.external_name = "first_in_the_admin"
        first.save()
        ProgramNavigator.objects.filter(program=self.program(), navigator__external_name=NAV).update(order=1)
        ProgramNavigator.objects.create(program=self.program(), navigator=first, order=0)

        self.apply(self.payload)

        self.assertEqual(self.navigator_names(), ["first_in_the_admin", NAV])


class LogTests(ApplyProgramBase):
    def test_every_apply_writes_a_log_entry(self) -> None:
        self.apply(self.payload, "--source", "programs/white_labels/co/example/spec.md", "--spec-commit", "abc1234")
        self.apply(self.payload)

        logs = list(ProgramImportLog.objects.order_by("applied_at"))
        self.assertEqual(len(logs), 2)
        first = logs[0]
        self.assertEqual(first.program, self.program())
        self.assertEqual((first.white_label_code, first.program_name), ("co", PROGRAM))
        self.assertEqual(first.payload, self.payload)
        self.assertEqual((first.source, first.spec_commit), ("programs/white_labels/co/example/spec.md", "abc1234"))
        self.assertIn(f"navigator '{NAV}': link", first.changes)

    def test_a_dry_run_changes_nothing_and_logs_nothing(self) -> None:
        output = self.apply(self.payload, "--dry-run")

        self.assertIn("Changes (to apply):", output)
        self.assertIn("Dry run complete — nothing changed.", output)
        self.assertFalse(Program.objects.exists())
        self.assertFalse(Navigator.objects.exists())
        self.assertFalse(ProgramImportLog.objects.exists())
