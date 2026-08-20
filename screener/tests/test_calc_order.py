"""
Guards `screener.views.CALC_ORDER` against the failure it is the only defense for.

A calculator that calls `self.program_eligible("x")` — or its member-scope sibling
`member_program_eligible` — reads x's computed result out of
`data`, which holds only the programs already calculated. Correctness therefore rests
entirely on the ordering in CALC_ORDER, and nothing else asserts it. If an upstream
program lost its slot, or a gating program were ordered ahead of what it depends on, the
dependent program would raise DependencyError and silently drop out of every household's
results on that white label.

The gating call sites are discovered by reading the source rather than listed here, so a
new gating program is covered by these tests the day it is written.
"""

import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from django.test import SimpleTestCase

from screener.views import CALC_ORDER, medicaid_program_codes

PROGRAMS_ROOT = Path(__file__).resolve().parents[2] / "programs" / "programs"


def _registered_program_codes() -> set:
    """Every program code a calculator backs, across both engines. The custom-calculator
    registry excludes PolicyEngine by design, and many upstreams (state Medicaid, nslp, chp)
    are PolicyEngine-backed, so a code is only found in the union."""
    from integrations.clients.policyengine.registry import all_calculators
    from programs.programs import calculators

    return set(calculators) | set(all_calculators)


def _string_assignments(class_node: ast.ClassDef) -> dict:
    """Class attributes assigned a plain string, or a list/tuple of plain strings.

    `program_eligible` is called two ways: with a literal, and with a loop variable over
    a class attribute holding a list of codes (CESN's `presumptive_eligibility`). Both
    are dependencies and both must be discovered, or the loop form is silently unguarded.
    """
    values = {}
    for stmt in class_node.body:
        if not isinstance(stmt, ast.Assign):
            continue
        names = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
        if not names:
            continue
        node = stmt.value
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            resolved = [node.value]
        elif isinstance(node, (ast.List, ast.Tuple)):
            resolved = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            # A starred or computed element means the list is not fully known here.
            if len(resolved) != len(node.elts):
                continue
        else:
            continue
        for name in names:
            values[name] = resolved
    return values


def _gate_arguments(class_node: ast.ClassDef, attrs: dict) -> list:
    """Every program code passed to `self.program_eligible(...)` inside this class.

    Resolves a literal argument directly, and a loop variable back to the class attribute
    it iterates. An argument that resolves to neither is reported so it cannot pass
    unnoticed.
    """
    codes, unresolved = [], []
    # Loop variable -> the attribute it iterates: `for program in self.presumptive_eligibility`
    loop_sources = {}
    for node in ast.walk(class_node):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            it = node.iter
            if isinstance(it, ast.Attribute) and it.attr in attrs:
                loop_sources[node.target.id] = it.attr
            elif isinstance(it, ast.Name) and it.id in attrs:
                loop_sources[node.target.id] = it.id

    for node in ast.walk(class_node):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("program_eligible", "member_program_eligible", "any_program_eligible")
            and node.args
        ):
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            codes.append(arg.value)
        elif isinstance(arg, ast.Name) and arg.id in loop_sources:
            codes.extend(attrs[loop_sources[arg.id]])
        elif isinstance(arg, ast.Attribute) and arg.attr in attrs:
            codes.extend(attrs[arg.attr])
        else:
            unresolved.append(ast.dump(arg))
    return codes, unresolved


def _program_code(class_node: ast.ClassDef) -> Optional[str]:
    """The `program_code` a calculator class declares, if it declares one."""
    for stmt in class_node.body:
        if (
            isinstance(stmt, ast.Assign)
            and any(getattr(t, "id", None) == "program_code" for t in stmt.targets)
            and isinstance(stmt.value, ast.Constant)
        ):
            return stmt.value.value
    return None


def find_program_gates():
    """Every (path, gating program_code, depended-on program code) in the tree."""
    gates = []
    for path in PROGRAMS_ROOT.rglob("*.py"):
        if "/tests/" in path.as_posix():
            continue
        source = path.read_text()
        if "program_eligible" not in source:
            continue
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.ClassDef):
                continue
            attrs = _string_assignments(node)
            codes, _ = _gate_arguments(node, attrs)
            gating_code = _program_code(node)
            for upstream_code in sorted(set(codes)):
                gates.append((path, gating_code, upstream_code))
    return gates


def find_unresolved_gate_arguments():
    """Call sites whose argument this test could not resolve to a program code."""
    unresolved = []
    for path in PROGRAMS_ROOT.rglob("*.py"):
        if "/tests/" in path.as_posix():
            continue
        source = path.read_text()
        if "program_eligible" not in source:
            continue
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.ClassDef):
                continue
            _, bad = _gate_arguments(node, _string_assignments(node))
            for dump in bad:
                unresolved.append((path, dump))
    return unresolved


class TestProgramGatesAreDiscoverable(SimpleTestCase):
    def test_gates_exist(self):
        """A regex that matched nothing would make every test below vacuously pass."""
        self.assertNotEqual(find_program_gates(), [], "found no program_eligible() call sites")

    def test_every_gate_argument_resolves_to_a_program_code(self):
        """A call this test cannot resolve is a call it cannot guard. Failing here is the
        signal to teach `_gate_arguments` the new form, not to skip the call site."""
        unresolved = find_unresolved_gate_arguments()
        self.assertEqual(
            unresolved,
            [],
            f"program_eligible() called with an argument this test cannot resolve: {unresolved}",
        )

    def test_loop_form_call_sites_are_discovered(self):
        """The CESN affordability programs pass a loop variable over
        `presumptive_eligibility` rather than a literal. Regex-based discovery missed
        these, leaving them unguarded; this pins that they are found."""
        found = {(g, u) for _, g, u in find_program_gates()}
        self.assertIn(("cesn_xceleap", "cesn_leap"), found)
        self.assertIn(("cesn_xceleap", "cesn_cowap"), found)
        self.assertIn(("cesn_bheap", "cesn_care"), found)

    def test_every_gating_calculator_declares_a_program_code(self):
        for path, gating_code, _ in find_program_gates():
            with self.subTest(path=path.name):
                self.assertIsNotNone(gating_code, f"{path} gates on another program but declares no program_code")


class TestUpstreamsAreOrderedBeforeTheirDependents(SimpleTestCase):
    """The invariant the raise in `ProgramCalculator.program_eligible` depends on."""

    def test_depended_on_programs_are_in_calc_order(self):
        for path, _, upstream_code in find_program_gates():
            with self.subTest(path=path.name, upstream=upstream_code):
                self.assertIn(
                    upstream_code,
                    CALC_ORDER,
                    f"{path.name} gates on {upstream_code}, which has no slot in CALC_ORDER, "
                    "so it may be calculated after its dependents",
                )

    def test_upstream_is_ordered_before_each_program_that_gates_on_it(self):
        for path, gating_code, upstream_code in find_program_gates():
            if gating_code not in CALC_ORDER:
                # Unlisted programs sort last, which is after every listed Medicaid.
                continue
            with self.subTest(gating=gating_code, upstream=upstream_code):
                self.assertLess(
                    CALC_ORDER.index(upstream_code),
                    CALC_ORDER.index(gating_code),
                    f"{upstream_code} must be calculated before {gating_code}, which gates on it",
                )

    def test_gated_programs_depend_on_a_real_registered_program(self):
        """Catches a typo'd or renamed program code, which would otherwise only show up as
        the dependent program going missing from results."""
        registered = _registered_program_codes()

        for path, _, upstream_code in find_program_gates():
            with self.subTest(path=path.name, upstream=upstream_code):
                self.assertIn(
                    upstream_code,
                    registered,
                    f"{path.name} gates on {upstream_code}, which no calculator backs",
                )


class TestEveryEntryEarnsItsSlot(SimpleTestCase):
    """A hand-listed slot only does something if something gates on that program. A program
    that merely gates on others needs no slot: unlisted sorts last, which is already after
    everything it reads. Listing one anyway asserts an ordering nothing depends on, and a
    reader cannot tell that from the tuple.

    The derived Medicaid block is exempt: those slots are deliberately pre-emptive, so the
    first program to gate on a state's Medicaid finds it already ordered."""

    def test_no_hand_listed_entry_is_ordering_nothing(self):
        upstreams = {upstream for _, _, upstream in find_program_gates()}
        derived = set(medicaid_program_codes())

        idle = [name for name in CALC_ORDER if name not in derived and name not in upstreams]
        self.assertEqual(
            idle,
            [],
            f"CALC_ORDER entries that nothing gates on: {idle}. Either a gate was removed "
            "and the slot outlived it, or the program only gates on others — in which case "
            "it sorts last anyway and needs no slot.",
        )


class TestMedicaidProgramCodes(SimpleTestCase):
    """The Medicaid block is derived from the `Medicaid` class hierarchy, not listed."""

    def test_every_medicaid_calculator_gets_a_slot(self):
        """The bug this replaces: a hand-maintained list omitted ma_mass_health and
        wa_apple_health_medicaid, so an MA or WA program gating on its own Medicaid found
        no slot and raised, vanishing from results."""
        for name in medicaid_program_codes():
            with self.subTest(name=name):
                self.assertIn(name, CALC_ORDER)

    def test_the_states_the_old_list_omitted_are_included(self):
        codes = medicaid_program_codes()
        self.assertIn("ma_mass_health", codes)
        self.assertIn("wa_apple_health_medicaid", codes)

    def test_the_abstract_base_is_not_included(self):
        """`Medicaid` itself backs no row; including it would put a non-existent program in
        the ordering."""
        self.assertNotIn("medicaid", medicaid_program_codes())

    def test_all_are_ordered_before_the_programs_that_gate_on_them(self):
        """Every Medicaid slot precedes any listed program that reads a Medicaid result, so
        the derived block cannot drift after its dependents."""
        derived = set(medicaid_program_codes())

        for _, gating, upstream in find_program_gates():
            if upstream not in derived or gating not in CALC_ORDER:
                continue
            with self.subTest(gating=gating, upstream=upstream):
                self.assertLess(CALC_ORDER.index(upstream), CALC_ORDER.index(gating))

    def test_derivation_sees_every_subclass_in_a_fresh_interpreter(self):
        """`__subclasses__()` only sees imported classes, so this derivation depends on the
        calculator packages having been walked. Guards that in a subprocess, where nothing
        else has imported them first."""
        script = (
            "import django, os;"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'benefits.settings');"
            "django.setup();"
            "from screener.views import medicaid_program_codes;"
            "print(','.join(medicaid_program_codes()))"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[2],
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        codes = result.stdout.strip().splitlines()[-1].split(",")
        self.assertIn("ma_mass_health", codes)
        self.assertIn("wa_apple_health_medicaid", codes)
        self.assertEqual(sorted(codes), sorted(medicaid_program_codes()))

    def test_every_derived_code_is_backed_by_a_calculator(self):
        registered = _registered_program_codes()

        for name in medicaid_program_codes():
            with self.subTest(name=name):
                self.assertIn(name, registered)

    def test_no_duplicates_in_calc_order(self):
        """A duplicate would make index() return the first slot and silently mislead the
        ordering assertions above."""
        self.assertEqual(len(CALC_ORDER), len(set(CALC_ORDER)))
