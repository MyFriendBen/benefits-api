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
    ProgramRecordImport,
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


class RecordSyncBase(TestCase):
    """A white label, poverty tables, a category, a temporary program-ops checkout, and mocked translation."""

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
        self.program_ops_dir = root / "program-ops"
        self.program_ops_dir.mkdir()

        from programs.management.commands.import_program_records import Command

        patcher = patch.object(Command, "PROGRAM_OPS_DIR", self.program_ops_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

        calculators = patch(
            "programs.management.commands.import_program_records.all_calculator_classes",
            return_value={PROGRAM: MagicMock(), OTHER: MagicMock()},
        )
        calculators.start()
        self.addCleanup(calculators.stop)

        translate = patch("programs.management.commands._program_record_sync.Translate")
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
        """Run the import and return its output. A run with failed records exits with an error after
        printing everything; that's expected here, and `self.records_failed` says whether it did."""
        out = io.StringIO()
        self.records_failed = False
        try:
            call_command("import_program_records", *args, stdout=out, stderr=io.StringIO())
        except CommandError as e:
            if "record(s) failed" not in str(e):
                raise
            self.records_failed = True
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


class RecordSyncTestCase(RecordSyncBase):
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
        baseline = ProgramRecordImport.objects.get(filename=f"{PROGRAM}_program_record.json").applied_record
        self.assertEqual(baseline["program.description"], "Help buying food.")
        self.assertTrue(baseline[f"link:document:{PROGRAM}_id"])

    def test_a_second_run_finds_nothing_to_change(self) -> None:
        self.import_record()

        output = self.run_import()

        self.assertIn("Matches the record", output)
        self.assertRegex(output, r"Current:\s+1")

    # ------------------------------------------------------------------ three-way labels

    def test_a_record_change_is_applied(self) -> None:
        self.import_record()
        self.record["program"]["description"] = "Help buying groceries."
        self.write(self.record)

        output = self.run_import()

        self.assertIn("Record changes (applied)", output)
        self.assertEqual(self.english(self.program().description), "Help buying groceries.")
        self.assertRegex(output, r"Updated:\s+1")

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
        ProgramRecordImport.objects.update(applied_record=None)
        self.admin_edit(self.program().name, "Name from the admin")
        self.record["program"]["estimated_decision_time"] = "21 days"
        self.write(self.record)

        output = self.run_import()

        program = self.program()
        self.assertEqual(self.english(program.estimated_decision_time), "21 days")
        self.assertEqual(self.english(program.name), "Name from the admin")
        self.assertIn("Admin edits (kept", output)

    def test_without_a_baseline_a_flag_switched_off_in_the_admin_is_kept(self) -> None:
        """False is a choice, not an empty field: the first run under this importer leaves it."""
        self.import_record()
        ProgramRecordImport.objects.update(applied_record=None)
        Program.objects.filter(pk=self.program().pk).update(show_on_current_benefits=False)

        output = self.run_import()

        self.assertFalse(self.program().show_on_current_benefits)
        self.assertIn("Admin edits (kept", output)
        self.assertIn("program.show_on_current_benefits", output)

    def test_without_a_baseline_a_link_removed_in_the_admin_is_kept(self) -> None:
        self.import_record()
        ProgramRecordImport.objects.update(applied_record=None)
        self.program().documents.clear()

        output = self.run_import()

        self.assertFalse(self.program().documents.exists())
        self.assertIn(f"document '{PROGRAM}_id': unlinked in the admin", output)

    def test_a_new_program_keeps_an_admin_edit_to_a_shared_row_it_lists(self) -> None:
        """Creating a program doesn't make its record newer than an admin edit to a row others show."""
        self.import_record()
        self.admin_edit(Navigator.objects.get(external_name=f"{PROGRAM}_nav_a").description, "Admin fixed text")
        # The new record takes the navigator over; the existing one now only references it.
        owned = self.record["navigators"][0]
        self.record["navigators"][0] = {"external_name": owned["external_name"]}
        self.write(self.record)
        other = make_record(OTHER)
        other["documents"] = []
        other["warning_message"] = {"external_name": f"{OTHER}_waitlist", "calculator": "_show", "message": "Wait"}
        other["navigators"] = [dict(owned, description="Older text")]
        self.write(other, OTHER)

        output = self.run_import()

        navigator = Navigator.objects.get(external_name=f"{PROGRAM}_nav_a")
        self.assertEqual(self.english(navigator.description), "Admin fixed text")
        self.assertIn(f"navigator:{PROGRAM}_nav_a.description: database", output)
        self.assertTrue(
            ProgramNavigator.objects.filter(program=self.program(OTHER), navigator=navigator).exists(),
            "the new program still links it",
        )

    def test_one_admin_edit_can_be_reverted_and_the_others_kept(self) -> None:
        self.import_record()
        program = self.program()
        self.admin_edit(program.description, "Edited in the admin.")
        self.admin_edit(program.name, "Name from the admin")
        record_file = f"{PROGRAM}_program_record.json"

        preview = self.run_import("--dry-run")
        self.assertIn(f"revert with --revert-admin-edit {record_file}:program.description", preview)

        output = self.run_import("--revert-admin-edit", f"{record_file}:program.description")

        program = self.program()
        self.assertEqual(self.english(program.description), "Help buying food.")
        self.assertEqual(self.english(program.name), "Name from the admin")
        self.assertIn("Admin edits (reverted to the record)", output)
        self.assertRegex(output, r"Admin edits kept:\s+1")

    def test_a_revert_hint_for_a_name_with_spaces_is_quoted_and_works(self) -> None:
        self.record["documents"] = [{"external_name": "photo id", "text": "A photo ID"}]
        self.import_record()
        self.admin_edit(Document.objects.get(external_name="photo id").text, "Edited in the admin.")
        argument = f"{PROGRAM}_program_record.json:document:photo id.text"

        preview = self.run_import("--dry-run")
        self.assertIn(f"revert with --revert-admin-edit '{argument}'", preview)

        self.run_import("--revert-admin-edit", argument)
        self.assertEqual(self.english(Document.objects.get(external_name="photo id").text), "A photo ID")

    def test_a_phone_number_in_another_format_is_not_an_admin_edit_next_run(self) -> None:
        self.record["navigators"][0]["phone_number"] = "+1 303-555-0100"
        self.import_record()

        output = self.run_import()

        self.assertRegex(output, r"Admin edits kept:\s+0")
        self.assertRegex(output, r"Current:\s+1")

    def test_an_explicit_null_base_program_is_accepted(self) -> None:
        self.record["program"]["base_program"] = None

        self.import_record()

        self.assertFalse(self.records_failed)
        self.assertIsNone(self.program().base_program)

    def test_a_category_scoped_to_another_white_label_fails(self) -> None:
        texas = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        ProgramCategory.objects.new_program_category(texas.code, "tx_only", "tx_only")
        self.record["program_category"] = {"external_name": "tx_only"}

        output = self.import_record()

        self.assertIn("belongs to the 'tx' white label", output)
        self.assertFalse(Program.objects.filter(name_abbreviated=PROGRAM).exists())

    def test_an_unnamed_row_linked_in_the_admin_is_left_alone(self) -> None:
        self.import_record()
        unnamed = Document.objects.new_document(white_label="co", external_name="unnamed_tmp")
        unnamed.external_name = None
        unnamed.save()
        self.program().documents.add(unnamed)
        Document.objects.new_document(white_label="co", external_name="admin_doc")
        self.program().documents.add(Document.objects.get(external_name="admin_doc"))

        self.run_import()

        self.assertFalse(self.records_failed)
        self.assertIn(unnamed, self.program().documents.all())

    def test_reverting_an_admin_edit_that_isnt_there_fails_the_record(self) -> None:
        self.import_record()

        output = self.run_import("--revert-admin-edit", f"{PROGRAM}_program_record.json:program.name")

        self.assertIn("names no admin edit in this record: program.name", output)

    def test_reverting_an_admin_edit_in_a_record_not_in_the_run_fails(self) -> None:
        self.write(self.record)

        with self.assertRaisesMessage(CommandError, "a record this run doesn't import: missing.json"):
            self.run_import("--revert-admin-edit", "missing.json:program.name")

    def test_a_navigator_email_is_copied_not_translated(self) -> None:
        """An email is an address, not text: every language gets the English value (MFB-2292)."""
        self.import_record()

        email = Navigator.objects.get(external_name=f"{PROGRAM}_nav_a").email
        self.assertTrue(email.no_auto)
        # setUp's mock translates into es and vi only.
        texts = {row.language_code: row.text for row in email.translations.filter(language_code__in=["es", "vi"])}
        self.assertEqual(texts, {"es": "a@example.org", "vi": "a@example.org"})

    # ------------------------------------------------------------------ active

    def test_a_record_without_active_never_switches_a_program(self) -> None:
        self.import_record()
        Program.objects.filter(pk=self.program().pk).update(active=True)

        output = self.run_import()

        self.assertTrue(self.program().active)
        self.assertNotIn("program.active", output)

    def test_a_record_that_sets_active_fails(self) -> None:
        """Switching a program on is a release decision made in the admin, so a record can't carry it."""
        self.record["program"]["active"] = True

        output = self.import_record()

        self.assertIn("program.active isn't a record field", output)
        self.assertFalse(Program.objects.filter(name_abbreviated=PROGRAM).exists())

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


class RunTestCase(RecordSyncBase):
    """What a run reads, what it waits for, and how it fails."""

    def test_a_dry_run_of_a_new_program_reports_its_failures(self) -> None:
        """A dry run applies inside a transaction it rolls back, so it fails where a real run would."""
        self.record["program"]["year"] = "1999"

        output = self.run_import_record_dry_run()

        self.assertIn("program.year '1999' has no FederalPovertyLimit row", output)
        self.assertFalse(Program.objects.filter(name_abbreviated=PROGRAM).exists())

    def run_import_record_dry_run(self) -> str:
        self.write(self.record)
        return self.run_import("--dry-run")

    def test_a_dry_run_of_a_new_program_creates_nothing(self) -> None:
        output = self.run_import_record_dry_run()

        self.assertRegex(output, r"To create:\s+1")
        self.assertFalse(Program.objects.filter(name_abbreviated=PROGRAM).exists())
        self.assertFalse(Navigator.objects.filter(external_name=f"{PROGRAM}_nav_a").exists())
        self.assertFalse(ProgramRecordImport.objects.exists())

    def test_a_new_program_without_its_calculator_waits(self) -> None:
        self.write(make_record("co_unbuilt"), program="co_unbuilt")

        output = self.run_import()

        self.assertIn("Waiting for a calculator, not created: co_unbuilt_program_record.json", output)
        self.assertFalse(Program.objects.filter(name_abbreviated="co_unbuilt").exists())

    def test_a_tracking_only_program_does_not_wait_for_a_calculator(self) -> None:
        record = make_record("co_tracking")
        record["program"]["has_calculator"] = False
        record["program_category"] = {"external_name": None}
        self.write(record, program="co_tracking")

        self.run_import()

        program = Program.objects.get(name_abbreviated="co_tracking")
        self.assertFalse(program.has_calculator)
        self.assertIsNone(program.category)

    def test_an_existing_program_is_updated_even_without_a_calculator(self) -> None:
        """The gate is about creating; a retired program whose calculator is gone still has a record."""
        self.import_record()
        self.record["program"]["description"] = "Retired."
        self.write(self.record)

        with patch("programs.management.commands.import_program_records.all_calculator_classes", return_value={}):
            self.run_import()

        self.assertEqual(self.english(self.program().description), "Retired.")

    def test_a_record_that_cannot_be_read_fails_alone(self) -> None:
        directory = self.program_ops_dir / "programs" / "white_labels" / "co" / "broken"
        directory.mkdir(parents=True)
        (directory / "broken_program_record.json").write_text("{not json", encoding="utf-8")

        output = self.import_record()

        self.assertIn("✗ broken_program_record.json: can't be read", output)
        self.assertTrue(Program.objects.filter(name_abbreviated=PROGRAM).exists())

    def test_failures_are_repeated_at_the_end_of_the_run(self) -> None:
        self.record["navigators"][0] = {"external_name": f"{PROGRAM}_nav_a", "description": "Only a description"}

        output = self.import_record()

        tail = output[output.rindex("need fixing before they import:") :]
        self.assertIn(f"✗ {PROGRAM}_program_record.json: navigators[0]", tail)
        self.assertFalse(Program.objects.filter(name_abbreviated=PROGRAM).exists())

    def test_a_failed_new_program_leaves_nothing_behind(self) -> None:
        self.record["program"]["legal_status_required"] = ["not_a_status"]

        self.import_record()

        self.assertFalse(Program.objects.filter(name_abbreviated=PROGRAM).exists())

    def test_a_run_with_a_failed_record_exits_with_an_error(self) -> None:
        self.record["program"]["year"] = "1999"
        self.write(self.record)
        self.write(make_record(OTHER), program=OTHER)

        with self.assertRaisesMessage(CommandError, "1 record(s) failed."):
            call_command("import_program_records", stdout=io.StringIO(), stderr=io.StringIO())

        self.assertTrue(Program.objects.filter(name_abbreviated=OTHER).exists(), "the other record still imports")

    def test_a_malformed_section_fails_its_record_not_the_run(self) -> None:
        self.record["documents"] = None
        self.write(self.record)
        self.write(make_record(OTHER), program=OTHER)

        output = self.run_import()

        self.assertIn("'documents' must be a list", output)
        self.assertTrue(Program.objects.filter(name_abbreviated=OTHER).exists())

    def test_a_record_without_a_white_label_code_fails_alone(self) -> None:
        self.record["white_label"] = {}
        self.write(self.record)
        self.write(make_record(OTHER), program=OTHER)

        output = self.run_import()

        self.assertIn("white_label has no 'code'", output)
        self.assertTrue(Program.objects.filter(name_abbreviated=OTHER).exists())

    def test_a_record_with_a_non_string_program_key_fails_alone(self) -> None:
        self.record["program"]["name_abbreviated"] = ["not", "a", "key"]
        self.write(self.record)
        self.write(make_record(OTHER), program=OTHER)

        output = self.run_import()

        self.assertIn("program has no 'name_abbreviated'", output)
        self.assertTrue(Program.objects.filter(name_abbreviated=OTHER).exists())

    def test_a_link_to_a_new_program_that_failed_comes_back_once_it_imports(self) -> None:
        # OTHER's record sorts first, so it links PROGRAM before PROGRAM fails and is removed.
        other = make_record(OTHER)
        other["program"]["required_programs"] = [PROGRAM]
        self.write(other, program=OTHER)
        self.record["program"]["year"] = "1999"
        self.write(self.record)

        self.run_import()
        self.assertTrue(self.records_failed)
        self.assertFalse(Program.objects.filter(name_abbreviated=PROGRAM).exists())

        self.record["program"]["year"] = "2025"
        self.write(self.record)
        self.run_import()

        self.assertFalse(self.records_failed)
        required = self.program(OTHER).required_programs.values_list("name_abbreviated", flat=True)
        self.assertEqual(list(required), [PROGRAM])

    def test_a_record_file_that_now_names_another_program_ignores_the_old_baseline(self) -> None:
        self.import_record()
        self.write(make_record(OTHER), program=OTHER)
        self.run_import()
        self.admin_edit(self.program(OTHER).description, "Edited in the admin.")
        # The first record's file now describes OTHER.
        moved = make_record(OTHER)
        moved["documents"] = [{"external_name": f"{OTHER}_id"}]
        moved["navigators"] = [{"external_name": f"{OTHER}_nav_a"}, {"external_name": f"{OTHER}_nav_b"}]
        moved["warning_message"] = {"external_name": f"{OTHER}_waitlist"}
        (self.program_ops_dir / "programs" / "white_labels" / "co" / OTHER / f"{OTHER}_program_record.json").unlink()
        self.write(moved)

        output = self.run_import()

        self.assertIn(f"was last applied to co/{PROGRAM}", output)
        self.assertEqual(self.english(self.program(OTHER).description), "Edited in the admin.")

    def test_two_records_for_one_program_fail_the_run(self) -> None:
        self.write(self.record)
        directory = self.program_ops_dir / "programs" / "white_labels" / "co" / "other"
        directory.mkdir(parents=True)
        (directory / "copy_program_record.json").write_text(json.dumps(self.record), encoding="utf-8")

        with self.assertRaisesMessage(CommandError, f"co/{PROGRAM} is declared twice"):
            self.run_import()

    def test_without_a_checkout_the_run_fails(self) -> None:
        with self.assertRaisesMessage(CommandError, "No program-ops checkout at"):
            self.run_import("--program-ops-dir", str(Path(self.temp_dir.name) / "missing"))

    def test_another_checkout_can_be_named(self) -> None:
        self.write(self.record)
        elsewhere = Path(self.temp_dir.name) / "elsewhere"
        self.program_ops_dir.rename(elsewhere)

        self.run_import("--program-ops-dir", str(elsewhere))

        self.assertTrue(Program.objects.filter(name_abbreviated=PROGRAM).exists())

    def test_each_import_updates_the_applied_time(self) -> None:
        self.import_record()
        row = ProgramRecordImport.objects.get(filename=f"{PROGRAM}_program_record.json")
        ProgramRecordImport.objects.filter(pk=row.pk).update(imported_at=row.imported_at.replace(year=2020))

        self.run_import()

        row.refresh_from_db()
        self.assertGreater(row.imported_at.year, 2020)

    def test_list_shows_when_each_record_was_applied(self) -> None:
        self.import_record()
        self.write(make_record(OTHER), program=OTHER)

        output = self.run_import("--list")

        self.assertIn(f"✓ {PROGRAM}_program_record.json: applied", output)
        self.assertIn(f"○ {OTHER}_program_record.json: never applied", output)

    def test_file_limits_the_run_to_one_record(self) -> None:
        self.write(self.record)
        self.write(make_record(OTHER), program=OTHER)

        self.run_import("--file", f"{OTHER}_program_record.json")

        self.assertTrue(Program.objects.filter(name_abbreviated=OTHER).exists())
        self.assertFalse(Program.objects.filter(name_abbreviated=PROGRAM).exists())


class ProgramRecordImportModelTest(TestCase):
    def test_str_names_the_file_and_program(self) -> None:
        row = ProgramRecordImport.objects.create(filename="co_snap_program_record.json", program_name="co_snap")

        self.assertIn("co_snap_program_record.json (co_snap)", str(row))
