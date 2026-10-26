"""
program-ops records keep their programs in line: every run compares each record with the database,
applies what the record changed, reports what the admin changed, and skips what both changed.
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
from django.test import TestCase

from programs.management.commands.export_program_record import BEGIN_MARKER, END_MARKER
from programs.models import (
    Document,
    FederalPoveryLimit,
    LegalStatus,
    Navigator,
    Program,
    ProgramCategory,
    ProgramConfigImport,
    ProgramNavigator,
)
from screener.models import WhiteLabel
from translations.models import Translation

PROGRAM = "co_test_program"
OTHER = "co_other_program"


def fake_translate(langs: list[str], texts: list[str], strict: bool = True) -> dict[str, dict[str, str]]:
    return {text: {lang: f"[{lang}] {text}" for lang in langs} for text in texts}


def make_record(program: str = PROGRAM) -> dict[str, Any]:
    return {
        "white_label": {"code": "co"},
        "program_category": {"external_name": "food"},
        "program": {
            "name_abbreviated": program,
            "legal_status_required": ["citizen"],
            "name": "Test Program",
            "description_short": "Food help",
            "description": "Help buying food.",
            "website_description": "Food help",
            "learn_more_link": "https://example.org/learn",
            "apply_button_link": "https://example.org/apply",
            "apply_button_description": "",
            "estimated_application_time": "30 minutes",
            "estimated_decision_time": "",
            "estimated_delivery_time": "",
            "estimated_value": "",
            "value_format": None,
            "year": "2025",
            "show_on_current_benefits": True,
            "has_calculator": True,
            "show_in_has_benefits_step": False,
        },
        "documents": [{"external_name": f"{program}_id", "text": "A photo ID"}],
        "navigators": [
            {
                "external_name": f"{program}_nav_a",
                "name": "Agency A",
                "email": "a@example.org",
                "description": "Helps with applications",
                "assistance_link": "https://example.org/a",
                "phone_number": "+13035550100",
            },
            {
                "external_name": f"{program}_nav_b",
                "name": "Agency B",
                "email": "b@example.org",
                "description": "Answers questions",
                "assistance_link": "https://example.org/b",
            },
        ],
        "warning_message": {"external_name": f"{program}_waitlist", "calculator": "_show", "message": "Waitlist only"},
    }


class RecordSyncTestCase(TestCase):
    def setUp(self) -> None:
        self.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")
        WhiteLabel.objects.create(name="Federal", code="federal")
        for status in ("citizen", "refugee"):
            LegalStatus.objects.create(status=status)
        for year in ("2025", "2026"):
            FederalPoveryLimit.objects.create(year=year, period=year)
        ProgramCategory.objects.new_program_category(None, "food", "food")

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.data_dir = root / "data"
        self.data_dir.mkdir()
        self.program_ops_dir = root / "program-ops"

        from programs.management.commands.import_all_program_configs import Command

        for attr, value in (("DATA_DIR", self.data_dir), ("PROGRAM_OPS_DIR", self.program_ops_dir)):
            patcher = patch.object(Command, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        calculators = patch(
            "programs.management.commands.import_all_program_configs.all_calculator_classes",
            return_value={PROGRAM: MagicMock(), OTHER: MagicMock()},
        )
        calculators.start()
        self.addCleanup(calculators.stop)

        for target in (
            "programs.management.commands.import_program_config.Translate",
            "programs.management.commands._program_record_sync.Translate",
        ):
            translate = patch(target)
            mock = translate.start()
            mock.return_value.bulk_translate.side_effect = fake_translate
            mock.languages = ["es", "vi"]
            self.addCleanup(translate.stop)

        self.record = make_record()

    # ------------------------------------------------------------------ helpers

    def write(self, record: dict[str, Any], program: str = PROGRAM) -> Path:
        directory = self.program_ops_dir / "programs" / "white_labels" / "co" / program
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{program}_program_record.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def run_import(self, *args: str) -> str:
        out = io.StringIO()
        call_command("import_all_program_configs", *args, stdout=out, stderr=io.StringIO())
        return out.getvalue()

    def import_record(self) -> str:
        self.write(self.record)
        return self.run_import()

    def program(self, name: str = PROGRAM) -> Program:
        return Program.objects.get(white_label__code="co", name_abbreviated=name)

    def english(self, translation: Translation) -> str:
        return translation.get_lang("en-us").text

    def admin_edit(self, translation: Translation, text: str) -> None:
        Translation.objects.edit_translation_by_id(translation.id, "en-us", text)

    # ------------------------------------------------------------------ creation and baseline

    def test_first_import_creates_the_program_and_stores_a_baseline(self) -> None:
        self.import_record()

        program = self.program()
        self.assertEqual(self.english(program.description), "Help buying food.")
        self.assertFalse(program.active)
        self.assertEqual(
            list(
                ProgramNavigator.objects.filter(program=program)
                .order_by("order")
                .values_list("navigator__external_name", flat=True)
            ),
            [f"{PROGRAM}_nav_a", f"{PROGRAM}_nav_b"],
        )
        baseline = ProgramConfigImport.objects.get(filename=f"{PROGRAM}_program_record.json").applied_record
        self.assertEqual(baseline["program.description"], "Help buying food.")
        self.assertTrue(baseline[f"link:document:{PROGRAM}_id"])

    def test_a_second_run_finds_nothing_to_change(self) -> None:
        self.import_record()

        output = self.run_import()

        self.assertIn("Matches the record", output)
        self.assertRegex(output, r"Records current:\s+1")

    # ------------------------------------------------------------------ three-way labels

    def test_a_record_change_is_applied(self) -> None:
        self.import_record()
        self.record["program"]["description"] = "Help buying groceries."
        self.write(self.record)

        output = self.run_import()

        self.assertIn("Record changes (applied)", output)
        self.assertEqual(self.english(self.program().description), "Help buying groceries.")
        self.assertRegex(output, r"Records updated:\s+1")

    def test_an_admin_edit_is_reported_and_kept(self) -> None:
        self.import_record()
        self.admin_edit(self.program().description, "Edited in the admin.")

        output = self.run_import()

        self.assertIn("Admin edits (kept", output)
        self.assertIn("program.description", output)
        self.assertEqual(self.english(self.program().description), "Edited in the admin.")
        self.assertRegex(output, r"Admin edits kept:\s+1")

        output = self.run_import()
        self.assertIn("Admin edits (kept", output, "an admin edit stays reported until the record matches")

    def test_reverting_admin_edits_applies_the_record(self) -> None:
        self.import_record()
        self.admin_edit(self.program().description, "Edited in the admin.")

        self.run_import("--revert-admin-edits")

        self.assertEqual(self.english(self.program().description), "Help buying food.")

    def test_a_field_changed_on_both_sides_is_a_conflict_and_skipped(self) -> None:
        self.import_record()
        self.admin_edit(self.program().description, "Edited in the admin.")
        self.record["program"]["description"] = "Edited in the record."
        self.write(self.record)

        output = self.run_import("--revert-admin-edits")

        self.assertIn("Conflicts", output)
        self.assertEqual(self.english(self.program().description), "Edited in the admin.")
        self.assertIn("Conflicts", self.run_import(), "a conflict stays a conflict until the two sides agree")

    def test_without_a_baseline_an_empty_field_is_filled_and_a_set_one_is_kept(self) -> None:
        """A program imported before baselines existed: nothing says which side moved."""
        self.import_record()
        ProgramConfigImport.objects.update(applied_record=None)
        self.admin_edit(self.program().name, "Name from the admin")
        self.record["program"]["estimated_decision_time"] = "21 days"
        self.write(self.record)

        output = self.run_import()

        program = self.program()
        self.assertEqual(self.english(program.estimated_decision_time), "21 days")
        self.assertEqual(self.english(program.name), "Name from the admin")
        self.assertIn("Admin edits (kept", output)

    # ------------------------------------------------------------------ active

    def test_a_record_without_active_never_switches_a_program(self) -> None:
        self.import_record()
        Program.objects.filter(pk=self.program().pk).update(active=True)

        output = self.run_import()

        self.assertTrue(self.program().active)
        self.assertNotIn("program.active", output)

    def test_a_record_that_sets_active_applies_it(self) -> None:
        self.import_record()
        self.record["program"]["active"] = True
        self.write(self.record)

        self.run_import()

        self.assertTrue(self.program().active)

    # ------------------------------------------------------------------ links

    def test_a_document_dropped_from_the_record_is_unlinked_not_deleted(self) -> None:
        self.import_record()
        del self.record["documents"]
        self.write(self.record)

        output = self.run_import()

        self.assertFalse(self.program().documents.exists())
        self.assertTrue(Document.objects.filter(external_name=f"{PROGRAM}_id").exists())
        self.assertIn("leaves it unused", output)

    def test_a_navigator_linked_in_the_admin_is_kept(self) -> None:
        self.import_record()
        program = self.program()
        extra = Navigator.objects.new_navigator(white_label="co", name="admin_nav")
        extra.external_name = "admin_nav"
        extra.save()
        ProgramNavigator.objects.create(program=program, navigator=extra, order=5)

        output = self.run_import()

        self.assertTrue(ProgramNavigator.objects.filter(program=program, navigator=extra).exists())
        self.assertIn("navigator 'admin_nav': linked in the admin, not in the record", output)

    def test_a_reference_links_a_shared_row_without_editing_it(self) -> None:
        shared = Document.objects.new_document(white_label="co", external_name="earned_income")
        Translation.objects.edit_translation_by_id(shared.text.id, "en-us", "Proof of income")
        self.record["documents"].append({"external_name": "earned_income"})

        self.import_record()
        self.record["documents"][1] = {"external_name": "earned_income"}
        self.write(self.record)
        self.run_import()

        self.assertTrue(self.program().documents.filter(external_name="earned_income").exists())
        self.assertEqual(self.english(Document.objects.get(external_name="earned_income").text), "Proof of income")

    def test_changing_an_owned_row_names_the_other_programs_that_show_it(self) -> None:
        self.import_record()
        other = Program.objects.new_program(white_label="co", name_abbreviated="co_neighbour")
        other.documents.add(Document.objects.get(external_name=f"{PROGRAM}_id"))
        self.record["documents"][0]["text"] = "A photo ID or passport"
        self.write(self.record)

        output = self.run_import()

        self.assertIn("is also shown on co/co_neighbour", output)
        self.assertEqual(
            self.english(Document.objects.get(external_name=f"{PROGRAM}_id").text), "A photo ID or passport"
        )

    def test_navigator_order_follows_the_record(self) -> None:
        self.import_record()
        self.record["navigators"].reverse()
        self.write(self.record)

        self.run_import()

        self.assertEqual(
            list(
                ProgramNavigator.objects.filter(program=self.program())
                .order_by("order")
                .values_list("navigator__external_name", flat=True)
            ),
            [f"{PROGRAM}_nav_b", f"{PROGRAM}_nav_a"],
        )

    def test_a_new_navigator_in_the_record_is_created_and_linked(self) -> None:
        self.import_record()
        self.record["navigators"].append(
            {
                "external_name": f"{PROGRAM}_nav_c",
                "name": "Agency C",
                "email": "",
                "description": "Walk-in help",
                "assistance_link": "https://example.org/c",
                "languages": ["es"],
            }
        )
        self.write(self.record)

        self.run_import()

        navigator = Navigator.objects.get(external_name=f"{PROGRAM}_nav_c")
        self.assertEqual(self.english(navigator.name), "Agency C")
        self.assertEqual(list(navigator.languages.values_list("code", flat=True)), ["es"])
        self.assertTrue(ProgramNavigator.objects.filter(program=self.program(), navigator=navigator).exists())

    # ------------------------------------------------------------------ program fields

    def test_program_fields_lists_and_year_update(self) -> None:
        self.import_record()
        self.record["program"].update(
            {"year": "2026", "legal_status_required": ["citizen", "refugee"], "show_in_has_benefits_step": True}
        )
        self.write(self.record)

        self.run_import()

        program = self.program()
        self.assertEqual(program.year.year, "2026")
        self.assertEqual(sorted(program.legal_status_required.values_list("status", flat=True)), ["citizen", "refugee"])
        self.assertTrue(program.show_in_has_benefits_step)

    def test_required_programs_resolve_across_records(self) -> None:
        self.record["program"]["required_programs"] = [OTHER]
        self.write(self.record)
        other = make_record(OTHER)
        self.write(other, program=OTHER)

        self.run_import()

        self.assertEqual(list(self.program().required_programs.values_list("name_abbreviated", flat=True)), [OTHER])

    # ------------------------------------------------------------------ translations

    def test_hand_edited_translations_are_kept_when_english_changes(self) -> None:
        self.import_record()
        description = self.program().description
        Translation.objects.edit_translation_by_id(description.id, "es", "Traducción a mano", manual=True)
        self.record["program"]["description"] = "Help buying groceries."
        self.write(self.record)

        output = self.run_import()

        description.refresh_from_db()
        self.assertEqual(description.get_lang("es").text, "Traducción a mano")
        self.assertEqual(description.get_lang("vi").text, "[vi] Help buying groceries.")
        self.assertIn("hand-edited translations are kept (es)", output)

    # ------------------------------------------------------------------ validation

    def test_a_partial_entry_fails_its_record(self) -> None:
        self.record["navigators"][0] = {"external_name": f"{PROGRAM}_nav_a", "description": "Only a description"}

        output = self.import_record()

        self.assertIn("partial entry", output)
        self.assertRegex(output, r"Failed:\s+1")
        self.assertFalse(Program.objects.filter(name_abbreviated=PROGRAM).exists())

    def test_an_unknown_key_fails_its_record(self) -> None:
        self.record["program"]["has_calculcator"] = True

        output = self.import_record()

        self.assertIn("unknown program key 'has_calculcator'", output)

    def test_two_records_owning_one_row_fail_the_run(self) -> None:
        self.write(self.record)
        other = make_record(OTHER)
        other["documents"] = [{"external_name": f"{PROGRAM}_id", "text": "A different text"}]
        self.write(other, program=OTHER)

        with self.assertRaisesMessage(CommandError, f"document '{PROGRAM}_id' is fully described by two records"):
            self.run_import()

    # ------------------------------------------------------------------ dry run, stdin, export

    def test_a_dry_run_changes_nothing(self) -> None:
        self.import_record()
        self.record["program"]["description"] = "Help buying groceries."
        self.write(self.record)

        output = self.run_import("--dry-run")

        self.assertIn("Record changes (to apply)", output)
        self.assertEqual(self.english(self.program().description), "Help buying food.")

    def test_records_can_arrive_on_stdin(self) -> None:
        bundle = {"files": {f"programs/white_labels/co/x/{PROGRAM}_program_record.json": json.dumps(self.record)}}

        with patch("sys.stdin", io.StringIO(json.dumps(bundle))):
            self.run_import("--program-ops-stdin")

        self.assertTrue(Program.objects.filter(name_abbreviated=PROGRAM).exists())

    def test_a_stdin_bundle_cannot_write_outside_its_directory(self) -> None:
        bundle = {"files": {"programs/../../etc/x_program_record.json": "{}"}}

        with patch("sys.stdin", io.StringIO(json.dumps(bundle))):
            with self.assertRaisesMessage(CommandError, "unexpected entry"):
                self.run_import("--program-ops-stdin")

    def test_an_export_carries_admin_edits_back_into_the_record(self) -> None:
        path = self.write(self.record)
        self.run_import()
        self.admin_edit(self.program().description, "Edited in the admin.")

        out = io.StringIO()
        call_command("export_program_record", "co", PROGRAM, "--record", str(path), stdout=out)
        text = out.getvalue()
        exported = json.loads(text[text.index(BEGIN_MARKER) + len(BEGIN_MARKER) : text.index(END_MARKER)])
        expected = copy.deepcopy(self.record)
        expected["program"]["description"] = "Edited in the admin."
        self.assertEqual(exported, expected)

        self.write(exported)
        self.assertIn("Matches the record", self.run_import())

    def test_a_new_program_starts_with_an_empty_decision_time(self) -> None:
        program = Program.objects.new_program(white_label="co", name_abbreviated="co_blank")

        self.assertEqual(self.english(program.estimated_decision_time), "")
