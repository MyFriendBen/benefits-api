"""Tests for the apply_translation_fixes management command."""

import csv
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from translations.models import Translation

SOURCE = "Are {subject} employed?"
BROKEN = "¿Está {sujeto} empleado?"
FIXED = "¿Está {subject} empleado?"


class ApplyTranslationFixesTest(TestCase):
    def setUp(self):
        Translation.objects.add_translation("test.renamed", default_message=SOURCE)
        Translation.objects.edit_translation("test.renamed", "es", BROKEN, manual=False)
        Translation.objects.add_translation("test.other", default_message=SOURCE)
        Translation.objects.edit_translation("test.other", "es", BROKEN, manual=False)

    def es_text(self, label: str) -> str:
        return Translation.objects.language("es").get(label=label).text

    def run_command(self, rows, *args, columns=("label", "lang", "prod_text", "staging_text")):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixes.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)
            out = StringIO()
            call_command("apply_translation_fixes", str(path), *args, stdout=out)
        return out.getvalue()

    def test_dry_run_changes_nothing(self):
        output = self.run_command([("test.renamed", "es", BROKEN, FIXED)])
        self.assertIn("Would update: 1", output)
        self.assertIn("Dry run", output)
        self.assertEqual(self.es_text("test.renamed"), BROKEN)

    def test_apply_writes_the_new_text(self):
        output = self.run_command([("test.renamed", "es", BROKEN, FIXED)], "--apply")
        self.assertIn("Updated: 1", output)
        self.assertEqual(self.es_text("test.renamed"), FIXED)

    def test_apply_leaves_other_rows_alone(self):
        self.run_command([("test.renamed", "es", BROKEN, FIXED)], "--apply")
        self.assertEqual(self.es_text("test.other"), BROKEN)

    def test_drifted_row_is_not_overwritten(self):
        Translation.objects.edit_translation("test.renamed", "es", "Texto editado {subject}")
        output = self.run_command([("test.renamed", "es", BROKEN, FIXED)], "--apply")
        self.assertIn("Drifted since the CSV was built (not touched): 1", output)
        self.assertEqual(self.es_text("test.renamed"), "Texto editado {subject}")

    def test_text_that_breaks_placeholders_is_refused(self):
        output = self.run_command([("test.renamed", "es", BROKEN, "¿Está {sujeto} empleado?!")], "--apply")
        self.assertIn("New text would break placeholders (not touched): 1", output)
        self.assertEqual(self.es_text("test.renamed"), BROKEN)

    def test_skip_leaves_the_row_alone(self):
        output = self.run_command([("test.renamed", "es", BROKEN, FIXED)], "--apply", "--skip", "test.renamed:es")
        self.assertIn("Skipped by --skip: 1", output)
        self.assertIn("Updated: 0", output)
        self.assertEqual(self.es_text("test.renamed"), BROKEN)

    def test_unknown_label_is_reported(self):
        output = self.run_command([("test.missing", "es", BROKEN, FIXED)], "--apply")
        self.assertIn("Row or label not found (not touched): 1", output)

    def test_missing_language_row_is_reported(self):
        output = self.run_command([("test.renamed", "xx", BROKEN, FIXED)], "--apply")
        self.assertIn("Row or label not found (not touched): 1", output)

    def test_edited_flag_is_preserved(self):
        Translation.objects.edit_translation("test.renamed", "es", BROKEN, manual=True)
        self.run_command([("test.renamed", "es", BROKEN, FIXED)], "--apply")
        self.assertTrue(Translation.objects.language("es").get(label="test.renamed").edited)

    def test_missing_csv_columns_raise(self):
        with self.assertRaises(CommandError):
            self.run_command([("test.renamed", "es", BROKEN)], columns=("label", "lang", "prod_text"))
