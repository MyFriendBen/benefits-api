"""
Tests for the add_translations management command.

The command reads a flat {label: english_text} JSON map, adds/updates English
rows, and batch auto-translates each unique English string to all supported
languages. These tests mock the Translation manager and the Translate client so
no database or external API is touched, and assert on the four behaviors that
matter: new/update/unchanged classification, dedup batching, --dry-run writing
nothing, and --no-translate skipping the translation API.
"""

import json
import os
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from typing import Optional


class AddTranslationsCommandTest(TestCase):
    def setUp(self) -> None:
        self.out = StringIO()
        self._tmp_paths = []

    def tearDown(self) -> None:
        for path in self._tmp_paths:
            try:
                os.unlink(path)
            except OSError:
                pass

    def _write_json(self, content):
        """Write `content` (str) to a temp file and return its path."""
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        self._tmp_paths.append(path)
        return path

    def _run(self, mapping, *args):
        """Call the command with `mapping` passed as a JSON file argument."""
        path = self._write_json(json.dumps(mapping))
        return call_command("add_translations", path, *args, stdout=self.out)

    def _mock_existing(self, label_to_english):
        """
        Build a Translation.objects mock whose .filter(label=...).first()
        returns an object reporting the given current English text (or None
        when the label is absent), so _classify can read it.
        """

        def make_obj(current_text):
            obj = MagicMock()
            obj.has_translation.return_value = current_text is not None
            obj.text = current_text
            return obj

        def filter_side_effect(label: Optional[str]=None, **_):
            qs = MagicMock()
            qs.first.return_value = make_obj(label_to_english[label]) if label in label_to_english else None
            return qs

        objects = MagicMock()
        objects.filter.side_effect = filter_side_effect
        # add_translation returns the (created/updated) parent object with an id.
        objects.add_translation.side_effect = lambda label, default_message, **_: MagicMock(id=label)
        return objects

    @patch("translations.management.commands.add_translations.Translate")
    @patch("translations.management.commands.add_translations.Translation")
    def test_classifies_new_update_unchanged(self, mock_translation, mock_translate) -> None:
        # "keep" already exists with identical text (unchanged),
        # "change" exists with different text (update),
        # "brand_new" does not exist (new).
        mock_translation.objects = self._mock_existing({"keep": "Same", "change": "Old text"})
        mock_translate.return_value.bulk_translate.return_value = {}

        self._run(
            {"keep": "Same", "change": "New text", "brand_new": "Fresh"},
            "--dry-run",
        )

        output = self.out.getvalue()
        self.assertIn("1 new", output)
        self.assertIn("1 English-text change", output)
        self.assertIn("1 unchanged", output)
        self.assertIn("+ brand_new", output)
        self.assertIn("~ change", output)

    @patch("translations.management.commands.add_translations.Translate")
    @patch("translations.management.commands.add_translations.Translation")
    def test_dry_run_writes_nothing_and_skips_api(self, mock_translation, mock_translate) -> None:
        mock_translation.objects = self._mock_existing({})
        translate_instance = mock_translate.return_value

        self._run({"a": "Alpha", "b": "Beta"}, "--dry-run")

        mock_translation.objects.add_translation.assert_not_called()
        mock_translation.objects.edit_translation_by_id.assert_not_called()
        translate_instance.bulk_translate.assert_not_called()
        self.assertIn("Dry run", self.out.getvalue())

    @patch("translations.management.commands.add_translations.Translate")
    @patch("translations.management.commands.add_translations.Translation")
    def test_no_translate_adds_english_only(self, mock_translation, mock_translate) -> None:
        mock_translation.objects = self._mock_existing({})
        translate_instance = mock_translate.return_value

        self._run({"a": "Alpha", "b": "Beta"}, "--no-translate")

        # English rows written, but the translation API never called.
        self.assertEqual(mock_translation.objects.add_translation.call_count, 2)
        translate_instance.bulk_translate.assert_not_called()

    @patch("translations.management.commands.add_translations.Translate")
    @patch("translations.management.commands.add_translations.Translation")
    def test_dedup_batches_identical_english(self, mock_translation, mock_translate) -> None:
        mock_translation.objects = self._mock_existing({})
        translate_instance = mock_translate.return_value
        # Echo back a translation per requested lang so fan-out has something to write.
        translate_instance.bulk_translate.side_effect = lambda langs, texts: {t: {"es": f"{t}-es"} for t in texts}

        # Three labels, two of which share identical English text.
        self._run({"x": "Shared", "y": "Shared", "z": "Unique"})

        # bulk_translate must be called once, with the DEDUPED unique texts only.
        translate_instance.bulk_translate.assert_called_once()
        _, called_texts = translate_instance.bulk_translate.call_args.args
        self.assertCountEqual(called_texts, ["Shared", "Unique"])

        # ...but the translated result fans out to all 3 labels (x and y both get it).
        written_ids = {call.args[0] for call in mock_translation.objects.edit_translation_by_id.call_args_list}
        self.assertEqual(written_ids, {"x", "y", "z"})

    @patch("translations.management.commands.add_translations.Translate")
    @patch("translations.management.commands.add_translations.Translation")
    def test_bulk_translate_failure_raises_after_english_saved(self, mock_translation, mock_translate) -> None:
        # The English rows are written before bulk_translate is attempted; if the
        # translation API raises, the command must surface a CommandError while the
        # already-saved English rows remain (the documented "re-run to recover" contract).
        mock_translation.objects = self._mock_existing({})
        mock_translate.return_value.bulk_translate.side_effect = Exception("Google API down")

        with self.assertRaises(CommandError) as ctx:
            self._run({"a": "Alpha", "b": "Beta"})

        # English rows were saved before the failure.
        self.assertEqual(mock_translation.objects.add_translation.call_count, 2)
        # No translated rows written, and the error tells the operator re-running recovers.
        mock_translation.objects.edit_translation_by_id.assert_not_called()
        self.assertIn("English rows were saved", str(ctx.exception))

    @patch("translations.management.commands.add_translations.Translation")
    def test_invalid_json_raises(self, mock_translation) -> None:
        path = self._write_json("not json")
        with self.assertRaises(CommandError):
            call_command("add_translations", path, stdout=self.out)

    @patch("translations.management.commands.add_translations.Translation")
    def test_non_object_json_raises(self, mock_translation) -> None:
        path = self._write_json('["a", "b"]')
        with self.assertRaises(CommandError):
            call_command("add_translations", path, stdout=self.out)

    @patch("translations.management.commands.add_translations.Translation")
    def test_non_string_value_raises(self, mock_translation) -> None:
        path = self._write_json('{"a": 123}')
        with self.assertRaises(CommandError):
            call_command("add_translations", path, stdout=self.out)
