"""
Guard against the dead-literal class of bug: reading a *base program* name through
`Screen.has_benefit()`.

`has_benefit()` is an exact `name_abbreviated` match, but no white label ships a program
literally named "snap" / "tanf" / "section_8" — they ship co_snap, ks_snap, wa_snap, …
So `has_benefit("snap")` is always False, and the categorical / adjunctive /
presumptive-eligibility branch it guards silently never fires. That shipped in ~14
calculators across CO, IL, KS, NC, TX and WA (and in the PolicyEngine `Snap` input, where
it meant every household looked like a SNAP non-recipient), which is what MFB-1382 fixed.

`has_base_benefit()` resolves the same question structurally through
`Program.base_program`, and `has_benefit_from_list()` accepts either kind of name, so
neither is constrained here — only the exact-match read is.

The source is parsed with `ast`, so prose in comments and docstrings that mentions the
old call doesn't trip the check.
"""

import ast
from pathlib import Path

from django.test import SimpleTestCase

from programs.models import BaseProgram

PROGRAMS_ROOT = Path(__file__).resolve().parent.parent
BASE_PROGRAM_NAMES = {value for value, _ in BaseProgram.choices}


def _base_program_literals(path: Path) -> list[tuple[int, str]]:
    """(lineno, literal) for every `*.has_benefit("<a base_program name>")` call."""
    tree = ast.parse(path.read_text(), filename=str(path))
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "has_benefit" or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and first.value in BASE_PROGRAM_NAMES:
            hits.append((node.lineno, first.value))
    return hits


class HasBenefitLiteralTests(SimpleTestCase):
    def test_no_calculator_reads_a_base_program_through_has_benefit(self):
        offenders = []
        for path in sorted(PROGRAMS_ROOT.rglob("*.py")):
            if "tests" in path.parts or path.name.startswith("test_"):
                continue
            for lineno, literal in _base_program_literals(path):
                offenders.append(f"{path.relative_to(PROGRAMS_ROOT.parent.parent)}:{lineno} has_benefit({literal!r})")

        self.assertEqual(
            offenders,
            [],
            "These reads are always False — a base_program name has no matching "
            "name_abbreviated in any white label. Use has_base_benefit(...) instead "
            "(or has_benefit_from_list([...]) for a mixed list):\n  " + "\n  ".join(offenders),
        )

    def test_detects_a_base_program_literal(self):
        """The walker actually finds what it's looking for (guards against a silent pass if
        the ast shape assumptions ever drift)."""
        source = "def f(screen):\n    return screen.has_benefit('snap')\n"
        path = Path(self._tmp_source(source))
        self.assertEqual(_base_program_literals(path), [(2, "snap")])

    def test_ignores_exact_program_names(self):
        """A white-label-specific name is a legitimate exact-match read."""
        source = "def f(screen):\n    return screen.has_benefit('wa_snap')\n"
        path = Path(self._tmp_source(source))
        self.assertEqual(_base_program_literals(path), [])

    def _tmp_source(self, source: str) -> str:
        import tempfile

        handle = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
        handle.write(source)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name
