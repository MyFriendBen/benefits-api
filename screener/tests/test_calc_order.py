"""
Guards `screener.views.CALC_ORDER` against the failure it is the only defense for.

A calculator that calls `self.program_eligible("x")` reads x's computed result out of
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
from pathlib import Path
from typing import Optional

from django.test import SimpleTestCase

from programs.framework.helpers import STATE_MEDICAID_OPTIONS
from screener.views import CALC_ORDER

PROGRAMS_ROOT = Path(__file__).resolve().parents[2] / "programs" / "programs"

# self.program_eligible("co_medicaid")
GATE_CALL = re.compile(r"""self\.program_eligible\(\s*["']([a-z0-9_]+)["']\s*\)""")


def _registered_program_codes() -> set:
    """Every program code a calculator backs, across both engines. The custom-calculator
    registry excludes PolicyEngine by design, and many upstreams (state Medicaid, nslp, chp)
    are PolicyEngine-backed, so a code is only found in the union."""
    from integrations.clients.policyengine.registry import all_calculators
    from programs.programs import calculators

    return set(calculators) | set(all_calculators)


def _program_code(source: str) -> Optional[str]:
    """The `program_code` a calculator module declares, if it declares one."""
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
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
        depends_on = GATE_CALL.findall(source)
        if not depends_on:
            continue
        gating_code = _program_code(source)
        for upstream_code in sorted(set(depends_on)):
            gates.append((path, gating_code, upstream_code))
    return gates


class TestProgramGatesAreDiscoverable(SimpleTestCase):
    def test_gates_exist(self):
        """A regex that matched nothing would make every test below vacuously pass."""
        self.assertNotEqual(find_program_gates(), [], "found no self.program_eligible() call sites")

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


class TestStateMedicaidOptions(SimpleTestCase):
    def test_all_options_are_ordered_before_the_unprefixed_emergency_medicaid(self):
        """CO's `emergency_medicaid` is spliced in directly after the Medicaid block; this
        keeps that relationship true if the tuple is reordered."""
        for name in STATE_MEDICAID_OPTIONS:
            with self.subTest(name=name):
                self.assertLess(CALC_ORDER.index(name), CALC_ORDER.index("emergency_medicaid"))

    def test_every_option_is_backed_by_a_calculator(self):
        registered = _registered_program_codes()

        for name in STATE_MEDICAID_OPTIONS:
            with self.subTest(name=name):
                self.assertIn(name, registered)

    def test_no_duplicates_in_calc_order(self):
        """A duplicate would make index() return the first slot and silently mislead the
        ordering assertions above."""
        self.assertEqual(len(CALC_ORDER), len(set(CALC_ORDER)))
