"""
White-label configs are large dict literals. A repeated key in a literal is not an error:
Python keeps the last entry and silently drops the first. That is how NC zip 28341 lost
Duplin County (MFB-2201). This test parses each config and fails on any repeated key.
"""

import ast
from pathlib import Path

from django.test import SimpleTestCase

WHITE_LABELS_DIR = Path(__file__).parent / "white_labels"


def duplicate_keys(source: str) -> list[tuple[int, str]]:
    """(line, key) for every constant key repeated within the same dict literal."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Dict):
            seen: set[object] = set()
            for key in node.keys:
                if isinstance(key, ast.Constant):
                    if key.value in seen:
                        found.append((key.lineno, repr(key.value)))
                    seen.add(key.value)
    return found


class TestWhiteLabelDictKeys(SimpleTestCase):
    def test_detects_a_repeated_key(self) -> None:
        self.assertEqual(duplicate_keys('{"28341": 1,\n "28341": 2}'), [(2, "'28341'")])

    def test_no_white_label_config_repeats_a_dict_key(self) -> None:
        # _template.py is a Jinja template, not valid Python.
        for path in sorted(WHITE_LABELS_DIR.glob("[!_]*.py")):
            with self.subTest(config=path.name):
                self.assertEqual(duplicate_keys(path.read_text()), [])
