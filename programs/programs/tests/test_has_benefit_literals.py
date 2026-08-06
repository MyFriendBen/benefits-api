"""
Guard against the dead-read class of bug: asking `Screen.has_benefit()` a question it
can't answer.

`has_benefit()` is an exact `name_abbreviated` match. Two ways that goes wrong:

1. **A base program name.** For `snap`, `tanf`, `wic` and `section_8` no white label
   ships a program under the bare name at all — they ship co_snap, ks_snap, wa_snap,
   ma_tafdc, wa_hcv, … So `has_benefit("snap")` was always False and the categorical /
   adjunctive / presumptive-eligibility branch it guarded silently never fired.

   `ssi` and `ssdi` are the partial case, and the reason this rule is a blanket ban
   rather than a per-name list: CO, IL, MA and NC *do* ship programs literally named
   `ssi` / `ssdi` (with `base_program` set to the same string), so an exact-match read
   worked in those four white labels and was dead in KS, WA, TX and MO, which use
   ks_ssdi / wa_ssi / tx_ssi / mo_ssi. A read that means "any variant of SSI" should say
   so structurally in every white label; `has_base_benefit("ssi")` is a superset of the
   exact read and correct everywhere, so there is no reason to keep the fragile form.

2. **A name held in a list.** Every one of those calculators reached the bad name by
   looping a class attribute — `presumptive_eligibility`, `categorically_eligible`,
   `auto_eligible_benefits` — so a check that only looked at string literals passed while
   production was broken.

   Note what this rule does *not* catch: a list entry that is neither a base program name
   nor a program the white label offers. The CESN energy calculators carried CO names
   (`leap`, `cowap`, `rtdlive`, `co_care`) that match nothing on a CESN screen, and no
   AST check can see that — it needs the program table. `test_presumptive_eligibility_resolution`
   covers the resolution seam; verifying a list against a white label's actual
   `show_in_has_benefits_step` programs is still unautomated.

So this module enforces one rule: **`has_benefit()` takes a string literal that is not a
base program name.** A non-literal argument means the caller is iterating a collection,
which is what `has_benefit_from_list()` is for — it resolves each entry as either an exact
name or a `base_program` group via `has_benefit_or_variant()`. Callers that need the
per-entry result (rather than "any of these") can call `has_benefit_or_variant()` directly.

`has_base_benefit()`, `has_benefit_from_list()` and `has_benefit_or_variant()` are all
unconstrained here — only the exact-match read is. `has_benefit` is defined on `Screen`
alone, so matching any `*.has_benefit(...)` receiver costs nothing today; member-level
lookups (`member.insurance.has_insurance_types()`) go by another name.

The source is parsed with `ast`, so prose in comments and docstrings that mentions the old
call doesn't trip the check.
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
    iterated, which hides case 1 from a literal-only check).
    """
    offenders = []
    for node in ast.walk(ast.parse(source, filename=filename)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "has_benefit" or not node.args:
            continue

        first = node.args[0]
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
        """The walker actually finds what it's looking for (guards against a silent pass if
        the ast shape assumptions ever drift)."""
        offenders = _has_benefit_offenders("def f(screen):\n    return screen.has_benefit('snap')\n")
        self.assertEqual(len(offenders), 1)
        self.assertEqual(offenders[0][0], 2)
        self.assertIn("base program name", offenders[0][1])

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
