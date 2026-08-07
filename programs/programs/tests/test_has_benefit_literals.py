"""
Guard: `Screen.has_benefit()` takes a string literal that is not a base program name.

`has_benefit()` is an exact `name_abbreviated` match, so a base program name never
resolves — white labels ship co_snap, ks_snap, wa_snap, ma_tafdc, wa_hcv, … and the
branch it guards silently never fires. A non-literal argument means the caller is
iterating a collection, which is how those names got in; that shape hides the first
rule from a literal-only check, so it's banned too.

`ssi` / `ssdi` are the reason this is a blanket ban rather than a per-name list: CO, IL,
MA and NC do ship programs under the bare name, so the exact read worked there and was
dead in KS, WA, TX and MO. `has_base_benefit("ssi")` is a superset and correct in every
white label.

Use `has_base_benefit(name)` for one base program, `has_benefit_from_list(names)` for a
list, or `has_benefit_or_variant(name)` when the per-entry result is needed. All three
are unconstrained here.

Not caught: a list entry that is neither a base program name nor a program the white
label offers (CESN carried CO names like `leap` and `rtdlive`). That needs the program
table, not the AST.
"""

import ast
from pathlib import Path

from django.test import SimpleTestCase

from programs.models import BaseProgram

PROGRAMS_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROGRAMS_ROOT.parent.parent
BASE_PROGRAM_NAMES = {value for value, _ in BaseProgram.choices}


def _has_benefit_offenders(source: str, filename: str = "<source>") -> list[tuple[int, str]]:
    """(lineno, reason) for every `*.has_benefit(...)` call that can't resolve.

    Flags a base program name (always False) and a non-literal argument (a list being
    iterated). The name is read positionally or from the `name_abbreviated` keyword.
    """
    offenders = []
    for node in ast.walk(ast.parse(source, filename=filename)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "has_benefit":
            continue

        if node.args:
            first = node.args[0]
        else:
            first = next((kw.value for kw in node.keywords if kw.arg == "name_abbreviated"), None)
            if first is None:
                continue

        if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
            rendered = ast.unparse(first)
            offenders.append((node.lineno, f"has_benefit({rendered}) — non-literal argument"))
        elif first.value in BASE_PROGRAM_NAMES:
            offenders.append((node.lineno, f"has_benefit({first.value!r}) — base program name"))
    return offenders


def _offenders_in_file(path: Path) -> list[tuple[int, str]]:
    return _has_benefit_offenders(path.read_text(), filename=str(path))


class HasBenefitLiteralTests(SimpleTestCase):
    def test_no_calculator_misuses_has_benefit(self):
        offenders = []
        for path in sorted(PROGRAMS_ROOT.rglob("*.py")):
            if "tests" in path.parts or path.name.startswith("test_"):
                continue
            for lineno, reason in _offenders_in_file(path):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno} {reason}")

        self.assertEqual(
            offenders,
            [],
            "has_benefit() is an exact name_abbreviated match against one white label's "
            "programs. A base program name never matches; a non-literal argument means a "
            "list is being iterated, which is how the base-program names got in. Use "
            "has_base_benefit(...) for a single base program, has_benefit_from_list([...]) "
            "for a list, or has_benefit_or_variant(name) when you need the per-entry "
            "result:\n  " + "\n  ".join(offenders),
        )

    def test_detects_a_base_program_literal(self):
        """The walker actually finds what it's looking for, so it can't silently stop
        working if the ast shape assumptions drift."""
        offenders = _has_benefit_offenders("def f(screen):\n    return screen.has_benefit('snap')\n")
        self.assertEqual(len(offenders), 1)
        self.assertEqual(offenders[0][0], 2)
        self.assertIn("base program name", offenders[0][1])

    def test_detects_a_base_program_passed_by_keyword(self):
        """A keyword argument has no node.args, so it must be read off node.keywords."""
        offenders = _has_benefit_offenders("def f(screen):\n    return screen.has_benefit(name_abbreviated='snap')\n")
        self.assertEqual(len(offenders), 1)
        self.assertEqual(offenders[0][0], 2)
        self.assertIn("base program name", offenders[0][1])

    def test_detects_a_non_literal_passed_by_keyword(self):
        offenders = _has_benefit_offenders(
            "def f(screen, name):\n    return screen.has_benefit(name_abbreviated=name)\n"
        )
        self.assertEqual(len(offenders), 1)
        self.assertIn("non-literal argument", offenders[0][1])

    def test_detects_a_loop_variable(self):
        """The shape that hid the original bug: the bad name lives in a class attribute."""
        source = (
            "class C:\n"
            "    presumptive_eligibility = ['snap', 'tanf']\n"
            "    def f(self):\n"
            "        return any(self.screen.has_benefit(p) for p in self.presumptive_eligibility)\n"
        )
        offenders = _has_benefit_offenders(source)
        self.assertEqual(len(offenders), 1)
        self.assertEqual(offenders[0][0], 4)
        self.assertIn("non-literal argument", offenders[0][1])

    def test_ignores_exact_program_names(self):
        """A white-label-specific name is a legitimate exact-match read."""
        self.assertEqual(_has_benefit_offenders("def f(screen):\n    return screen.has_benefit('wa_snap')\n"), [])

    def test_ignores_the_resolving_helpers(self):
        """has_base_benefit / has_benefit_from_list / has_benefit_or_variant are the fix, not
        the problem — including when they take a variable."""
        source = (
            "def f(screen, names, name):\n"
            "    return (\n"
            "        screen.has_base_benefit('snap')\n"
            "        or screen.has_benefit_from_list(names)\n"
            "        or screen.has_benefit_or_variant(name)\n"
            "    )\n"
        )
        self.assertEqual(_has_benefit_offenders(source), [])
