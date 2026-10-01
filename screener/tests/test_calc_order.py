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

from programs.framework.gates import force_calculated_codes, strict_upstream_fields
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


def _all_calculator_classes() -> dict:
    """Both engines' registries merged, so an upstream is found whichever backs it."""
    from integrations.clients.policyengine.registry import all_calculators
    from programs.programs import calculators

    return {**calculators, **all_calculators}


def _is_strict_gate(path, upstream_code: str) -> bool:
    """Whether `upstream_code` is read through the raising accessor in this file, rather
    than the tolerant `any_program_eligible`."""
    source = path.read_text()
    for node in ast.walk(ast.parse(source)):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("program_eligible", "member_program_eligible")
            and node.args
        ):
            continue
        argument = node.args[0]
        if isinstance(argument, ast.Constant) and argument.value == upstream_code:
            return True
    return False


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


class TestStrictGatesDeclareTheirUpstreamsDependencies(SimpleTestCase):
    """A strict gate raises when its upstream is absent from `data`, and a missing screener
    field is one way an upstream gets there: `can_calc()` drops it before it can be
    calculated. If the dependent needs fewer fields than the upstream, there are screens
    where the dependent runs and the upstream did not — so the gate raises and the program
    disappears for a household it could otherwise have answered for.

    `ProgramCalculator.all_dependencies` unions a strict upstream's fields automatically, so
    this now guards the derivation rather than 24 hand-written lists. Tolerant gates are
    exempt: `any_program_eligible` reads an absent upstream as "no" and degrades instead of
    vanishing.

    This test used to compare `upstream_cls.dependencies`, which is `()` on every
    PolicyEngine calculator — they carry dependencies per `pe_input` instead. The
    subtraction was therefore always empty and the test never checked any of the sixteen
    strict PolicyEngine edges, thirteen of which were under-declared. `strict_upstream_fields`
    reads whichever the upstream actually uses.
    """

    def test_a_strict_gates_dependencies_cover_its_upstreams(self):
        registries = _all_calculator_classes()
        offenders = []

        for path, gating, upstream in find_program_gates():
            if not _is_strict_gate(path, upstream):
                continue
            dependent_cls = registries.get(gating)
            if dependent_cls is None or upstream not in registries:
                continue
            uncovered = strict_upstream_fields((upstream,)) - set(dependent_cls.all_dependencies())
            if uncovered:
                offenders.append(f"{gating} gates on {upstream} but does not declare {sorted(uncovered)}")

        self.assertEqual(offenders, [], "; ".join(offenders))

    def test_a_policyengine_upstreams_fields_are_read_off_its_inputs(self):
        """The specific hole above: a PE upstream's screener fields live on its `pe_inputs`,
        not on a class attribute. Pins that the helper finds them, so the guard cannot go
        vacuous again."""
        registries = _all_calculator_classes()
        co_medicaid = registries["co_medicaid"]

        self.assertEqual(tuple(co_medicaid.dependencies), ())
        self.assertIn("household_assets", strict_upstream_fields(("co_medicaid",)))

    def test_strict_upstream_fields_follows_a_custom_upstreams_own_gates(self):
        """`il_aca_adults` gates on `il_family_care`, which gates in turn on `il_medicaid`.
        The chain has to be walked or the middle link hides the PE fields at the end."""
        self.assertIn("household_assets", strict_upstream_fields(("il_family_care",)))


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


class TestDeclarationsMatchTheCalls(SimpleTestCase):
    """`gates_on` / `gates_on_any` are the graph; this is the only thing keeping them true.

    Production reads the declarations — `can_calc` unions a strict upstream's fields,
    `screener.views` decides which upstreams to force-calculate, `CALC_ORDER` is checked
    against them. Nothing at runtime notices a gate that was added to the code and not to
    the declaration, which is why the `ast` walk stays: it is now a consistency check
    rather than the graph itself.
    """

    def _declared(self):
        registries = _all_calculator_classes()
        strict, tolerant = {}, {}
        for code, Calculator in registries.items():
            strict[code] = set(Calculator.gates_on)
            tolerant[code] = set(Calculator.gates_on_any)
        return strict, tolerant

    def _called(self):
        strict, tolerant = {}, {}
        for path, gating, upstream in find_program_gates():
            if gating is None:
                continue
            bucket = strict if _is_strict_gate(path, upstream) else tolerant
            bucket.setdefault(gating, set()).add(upstream)
        return strict, tolerant

    def test_every_call_is_declared(self):
        declared_strict, declared_tolerant = self._declared()
        called_strict, called_tolerant = self._called()

        missing = []
        for code, upstreams in called_strict.items():
            for undeclared in sorted(upstreams - declared_strict.get(code, set())):
                missing.append(f"{code} calls program_eligible({undeclared!r}) but does not declare it in gates_on")
        for code, upstreams in called_tolerant.items():
            for undeclared in sorted(upstreams - declared_tolerant.get(code, set())):
                missing.append(f"{code} reads {undeclared!r} tolerantly but does not declare it in gates_on_any")

        self.assertEqual(missing, [], "; ".join(missing))

    def test_no_declaration_is_stale(self):
        """A declaration outliving its call is not harmless: it keeps a `CALC_ORDER` slot
        alive and keeps forcing an upstream to be calculated on every screen."""
        declared_strict, declared_tolerant = self._declared()
        called_strict, called_tolerant = self._called()

        stale = []
        for code, upstreams in declared_strict.items():
            for orphan in sorted(upstreams - called_strict.get(code, set())):
                stale.append(f"{code} declares gates_on {orphan!r} but never calls program_eligible for it")
        for code, upstreams in declared_tolerant.items():
            for orphan in sorted(upstreams - called_tolerant.get(code, set())):
                stale.append(f"{code} declares gates_on_any {orphan!r} but never reads it")

        self.assertEqual(stale, [], "; ".join(stale))

    def test_an_undeclared_gate_raises_rather_than_reading_data(self):
        """The runtime half of the same invariant, for a gate written after this test ran."""
        from unittest.mock import Mock

        from programs.framework.base import Eligibility, ProgramCalculator

        class Undeclared(ProgramCalculator):
            program_code = "undeclared_test_only"

        calculator = Undeclared(Mock(), Mock(), {"co_medicaid": Eligibility()}, Mock())

        with self.assertRaises(ValueError):
            calculator.program_eligible("co_medicaid")


class TestForceCalculatedUpstreams(SimpleTestCase):
    """Which gated upstreams `screener.views` calculates regardless of configuration."""

    def test_every_custom_upstream_is_force_calculated(self):
        registries = _all_calculator_classes()
        from integrations.clients.policyengine.registry import all_calculators as pe_calculators

        upstreams = {upstream for _, _, upstream in find_program_gates()}
        custom = {u for u in upstreams if u in registries and u not in pe_calculators}

        self.assertEqual(custom, set(force_calculated_codes()))

    def test_no_policyengine_upstream_is_force_calculated(self):
        """Adding one to the batched request would merge its `pe_inputs` into the shared
        household payload, so it could move an unrelated active program's result."""
        from integrations.clients.policyengine.registry import all_calculators as pe_calculators

        self.assertEqual(set(force_calculated_codes()) & set(pe_calculators), set())

    def test_the_force_calculated_set_is_the_six_custom_upstreams(self):
        """Pinned by name so a new gate on a custom upstream is a visible diff here."""
        self.assertEqual(
            sorted(force_calculated_codes()),
            [
                "cesn_care",
                "cesn_cowap",
                "cesn_eoc",
                "cesn_leap",
                "il_family_care",
                "il_moms_and_babies",
            ],
        )

    def test_every_force_calculated_upstream_has_a_calc_order_slot(self):
        """It is calculated in the same loop, so it is subject to the same ordering."""
        for code in sorted(force_calculated_codes()):
            with self.subTest(code=code):
                self.assertIn(code, CALC_ORDER)
