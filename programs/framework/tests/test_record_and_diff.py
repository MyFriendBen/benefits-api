"""Tests for the pure parts of record_and_diff: the scenario diff, the override rewrite and the pin check."""

import ast
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest import skipUnless
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from conftest import PE_CAPTURE_DIR_ENV_VAR, record_test_outcome
from programs.management.commands.record_and_diff import (
    CHANGED,
    ERROR,
    FAILED,
    PASSED,
    REPO_ROOT,
    SKIPPED,
    UNCHANGED,
    Capture,
    Outcome,
    add_override,
    adopt,
    class_level_pins,
    classify_scenario,
    diff_captures,
    format_rewrite,
    load_capture,
    module_classes,
    pe_test_files,
    remove_override,
    require_module_level_pins,
    resolve_version,
    unreadable_module_pins,
)


def outcome(
    test: str, eligible: bool = True, value: int = 100, error: Optional[str] = None, version: str = "1.0.0"
) -> Outcome:
    return {"test": test, "pe_version": version, "eligible": eligible, "value": value, "error": error}


MODULE = "programs/x/tests/test_x.py"


class TestClassifyScenario(SimpleTestCase):
    def test_same_result_is_unchanged(self) -> None:
        self.assertEqual(classify_scenario(outcome("t"), outcome("t", version="2.0.0")), UNCHANGED)

    def test_a_moved_value_is_changed(self) -> None:
        self.assertEqual(classify_scenario(outcome("t"), outcome("t", value=101)), CHANGED)

    def test_a_flipped_eligibility_is_changed(self) -> None:
        self.assertEqual(classify_scenario(outcome("t"), outcome("t", eligible=False)), CHANGED)

    def test_an_error_after_recording_is_an_error(self) -> None:
        self.assertEqual(classify_scenario(outcome("t"), outcome("t", error="HTTPError: 422")), ERROR)

    def test_no_outcome_after_recording_is_an_error(self) -> None:
        self.assertEqual(classify_scenario(outcome("t"), None), ERROR)

    def test_a_scenario_new_since_the_baseline_is_changed(self) -> None:
        self.assertEqual(classify_scenario(None, outcome("t")), CHANGED)

    def test_a_failing_test_with_the_same_result_is_changed(self) -> None:
        # A per-member assertion can fail while eligibility and the total hold.
        self.assertEqual(classify_scenario(outcome("t"), outcome("t"), PASSED, FAILED), CHANGED)

    def test_a_test_failing_before_reaching_policyengine_is_an_error(self) -> None:
        self.assertEqual(classify_scenario(outcome("t"), None, PASSED, FAILED), ERROR)

    def test_a_test_that_never_ran_is_an_error(self) -> None:
        self.assertEqual(classify_scenario(outcome("t"), outcome("t"), PASSED, None), ERROR)

    def test_a_failing_baseline_is_an_error(self) -> None:
        self.assertEqual(classify_scenario(outcome("t"), outcome("t"), FAILED, PASSED), ERROR)

    def test_skipped_in_both_passes_is_unchanged(self) -> None:
        self.assertEqual(classify_scenario(None, None, SKIPPED, SKIPPED), UNCHANGED)

    def test_skipped_only_when_recording_is_an_error(self) -> None:
        self.assertEqual(classify_scenario(outcome("t"), None, PASSED, SKIPPED), ERROR)

    def test_a_passing_test_that_never_calls_policyengine_is_unchanged(self) -> None:
        self.assertEqual(classify_scenario(None, None, PASSED, PASSED), UNCHANGED)


class TestDiffCaptures(SimpleTestCase):
    def test_groups_scenarios_by_module_and_ranks_error_over_changed(self) -> None:
        a, b, c = f"{MODULE}::TestX::test_a", f"{MODULE}::TestX::test_b", f"{MODULE}::TestX::test_c"
        other = "programs/y/tests/test_y.py::TestY::test_a"
        tests = (a, b, c, other)
        baseline = Capture(scenarios={t: outcome(t) for t in tests}, tests={t: PASSED for t in tests})
        recorded = Capture(
            scenarios={
                a: outcome(a, value=5),
                b: outcome(b, error="boom"),
                c: outcome(c),
                other: outcome(other, version="2.0.0"),
            },
            tests={a: FAILED, b: FAILED, c: PASSED, other: PASSED},
        )

        diff = diff_captures("2.0.0", [MODULE, "programs/y/tests/test_y.py"], baseline, recorded)

        x = diff["modules"][MODULE]
        self.assertEqual(x["status"], ERROR)
        self.assertEqual(x["scenario_count"], 3)
        self.assertEqual([s["test"] for s in x["scenarios"]], [a, b])
        self.assertEqual(x["baseline_versions"], ["1.0.0"])
        self.assertEqual(diff["modules"]["programs/y/tests/test_y.py"]["status"], UNCHANGED)
        self.assertEqual(diff["summary"], {UNCHANGED: 1, CHANGED: 0, ERROR: 1})

    def test_a_module_with_no_test_outcomes_is_an_error(self) -> None:
        # Its tests never ran (a collection error, say), so adoption must hold it.
        empty = Capture(scenarios={}, tests={})

        diff = diff_captures("2.0.0", [MODULE], empty, empty)

        self.assertEqual(diff["modules"][MODULE]["status"], ERROR)

    def test_a_failing_test_with_no_capture_holds_its_module(self) -> None:
        test = f"{MODULE}::TestX::test_helper"
        baseline = Capture(scenarios={}, tests={test: PASSED})
        recorded = Capture(scenarios={}, tests={test: FAILED})

        diff = diff_captures("2.0.0", [MODULE], baseline, recorded)

        self.assertEqual(diff["modules"][MODULE]["status"], ERROR)


class TestLoadCapture(SimpleTestCase):
    def test_reads_scenarios_and_the_worst_outcome_per_test(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            capture_dir = Path(directory)
            (capture_dir / "outcomes").mkdir()
            (capture_dir / "gw0.jsonl").write_text(json.dumps(outcome("t")) + "\n")
            (capture_dir / "outcomes" / "gw0.jsonl").write_text(
                json.dumps({"test": "t", "outcome": PASSED})
                + "\n"
                + json.dumps({"test": "t", "outcome": FAILED})
                + "\n"
            )

            capture = load_capture(capture_dir)

        self.assertEqual(capture.scenarios, {"t": outcome("t")})
        self.assertEqual(capture.tests, {"t": FAILED})

    def test_a_directory_with_no_test_outcomes_is_rejected(self) -> None:
        # A mistyped --baseline would otherwise compare against nothing and call everything changed.
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CommandError):
                load_capture(Path(directory) / "missing")


class TestRecordTestOutcome(SimpleTestCase):
    def report(self, when: str, outcome: str) -> SimpleNamespace:
        return SimpleNamespace(
            nodeid="t", when=when, outcome=outcome, passed=outcome == PASSED, failed=outcome == FAILED
        )

    def test_writes_failures_and_call_passes_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", {PE_CAPTURE_DIR_ENV_VAR: directory, "PYTEST_XDIST_WORKER": "gw0"}):
                record_test_outcome(self.report("setup", PASSED))
                record_test_outcome(self.report("call", PASSED))
                record_test_outcome(self.report("teardown", FAILED))

            capture = load_capture(Path(directory))

        self.assertEqual(capture.tests, {"t": FAILED})

    def test_does_nothing_without_a_capture_directory(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            record_test_outcome(self.report("call", FAILED))


class TestResolveVersion(SimpleTestCase):
    served = {"current": "2.18.0", "frontier": "2.29.14"}

    def test_resolves_an_alias(self) -> None:
        self.assertEqual(resolve_version("frontier", self.served), "2.29.14")

    def test_accepts_an_exact_served_version(self) -> None:
        self.assertEqual(resolve_version("2.18.0", self.served), "2.18.0")

    def test_rejects_a_version_policyengine_no_longer_serves(self) -> None:
        with self.assertRaises(CommandError):
            resolve_version("2.9.0", self.served)

    def test_rejects_anything_else(self) -> None:
        with self.assertRaises(CommandError):
            resolve_version("latest", self.served)


class TestAdopt(SimpleTestCase):
    def test_refuses_when_every_module_errored(self) -> None:
        diff = {"target_version": "2.18.0", "modules": {MODULE: {"status": ERROR}, "b.py": {"status": ERROR}}}

        with patch("pathlib.Path.write_text") as write_text, self.assertRaises(CommandError):
            adopt(diff, Path("/nonexistent"), "2.9.0")

        write_text.assert_not_called()

    def test_writes_nothing_when_black_fails(self) -> None:
        diff = {"target_version": "2.18.0", "modules": {}}
        failed = subprocess.CompletedProcess(args=[], returncode=123, stdout="", stderr="cannot format")

        with (
            patch(f"{adopt.__module__}.subprocess.run", return_value=failed),
            patch("pathlib.Path.write_text") as write_text,
            self.assertRaisesMessage(CommandError, "black failed"),
        ):
            adopt(diff, Path("/nonexistent"), "2.9.0")

        write_text.assert_not_called()

    def _adopt_one(self, source: str, target: str) -> tuple[dict[str, list[str]], str, Path]:
        """Adopt ``target`` for one unchanged module written with ``source``; return the result and its file."""
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            module = root_path / MODULE
            module.parent.mkdir(parents=True)
            module.write_text(source)
            recorded = root_path / "recorded" / Path(MODULE).parent / "cassettes"
            recorded.mkdir(parents=True)
            (recorded / "TestA.test_one.yaml").write_text("recorded at the target")
            diff = {"target_version": target, "modules": {MODULE: {"status": UNCHANGED}}}

            with patch(f"{adopt.__module__}.REPO_ROOT", root_path):
                result = adopt(diff, root_path / "recorded", target)

            copied = module.parent / "cassettes" / "TestA.test_one.yaml"
            return result, module.read_text(), copied if copied.exists() else Path()

    def test_keeps_a_pin_newer_than_the_target(self) -> None:
        source = (
            'PE_VERSION = "2.145.6"\nPE_VERSION_REASON = "frontier input"\n\n\n'
            "class TestA(PeIntegrationTestCase):\n    pass\n"
        )

        result, after, copied = self._adopt_one(source, "2.130.0")

        self.assertEqual(result["ahead"], [MODULE])
        self.assertEqual(result["adopted"], [])
        self.assertEqual(after, source)
        self.assertEqual(copied, Path())

    @skipUnless(importlib.util.find_spec("black"), "black isn't installed")
    def test_removes_a_pin_older_than_the_target(self) -> None:
        result, after, copied = self._adopt_one(OVERRIDDEN, "2.130.0")

        self.assertEqual(result["adopted"], [MODULE])
        self.assertNotIn("PE_VERSION", after)
        self.assertNotEqual(copied, Path())


class TestFormatRewrite(SimpleTestCase):
    # black is in requirements-dev.txt, which CI's test step doesn't install.
    @skipUnless(importlib.util.find_spec("black"), "black isn't installed")
    def test_formats_with_the_repo_config(self) -> None:
        self.assertEqual(format_rewrite(REPO_ROOT / "x.py", "x = ( 1 )\n"), "x = 1\n")

    def test_rejects_invalid_python(self) -> None:
        with self.assertRaisesMessage(CommandError, "would break it"):
            format_rewrite(REPO_ROOT / "x.py", "def (\n")


OVERRIDDEN = '''"""Docstring."""

from harness import PeIntegrationTestCase

PE_VERSION = "1.815.1"
PE_VERSION_REASON = (
    "Recorded before the suite-wide pin. Remove PE_VERSION and this reason once the module is "
    "re-recorded at PE_TEST_VERSION."
)
YEAR = "2026"


class TestA(PeIntegrationTestCase):
    """Class docstring."""

    def test_one(self):
        pass


class TestB(PeIntegrationTestCase):
    screen_id = 1
'''


class TestOverrideRewrite(SimpleTestCase):
    def test_remove_strips_the_pin_and_its_reason(self) -> None:
        source = remove_override(OVERRIDDEN)

        self.assertNotIn("PE_VERSION", source)
        self.assertNotIn("pe_version", source)
        self.assertIn('YEAR = "2026"', source)
        self.assertIn("screen_id = 1", source)
        ast.parse(source)

    def test_add_then_remove_round_trips_to_no_override(self) -> None:
        bare = remove_override(OVERRIDDEN)

        pinned = add_override(bare, "2.9.0", "held for review")

        ast.parse(pinned)
        self.assertIn('PE_VERSION = "2.9.0"', pinned)
        self.assertIn('PE_VERSION_REASON = "held for review"', pinned)
        self.assertEqual(class_level_pins(pinned), [])
        self.assertNotIn("PE_VERSION", remove_override(pinned))

    def test_add_leaves_the_classes_alone(self) -> None:
        bare = remove_override(OVERRIDDEN)

        pinned = add_override(bare, "2.9.0", "held for review")

        self.assertEqual(pinned.split("class TestA")[1], bare.split("class TestA")[1])

    def test_module_classes(self) -> None:
        self.assertEqual(module_classes(OVERRIDDEN), ["TestA", "TestB"])


class TestClassLevelPins(SimpleTestCase):
    def test_module_constants_are_not_class_level_pins(self) -> None:
        self.assertEqual(class_level_pins(OVERRIDDEN), [])

    def test_finds_hardcoded_and_constant_class_pins(self) -> None:
        source = (
            "PE_VERSION = '2.9.0'\n\n\n"
            "class TestA(PeIntegrationTestCase):\n"
            "    pe_version = '2.145.6'\n"
            "    pe_version_reason: str = 'frontier'\n\n\n"
            "class TestB(PeIntegrationTestCase):\n"
            "    pe_version = PE_VERSION\n"
        )

        self.assertEqual(
            class_level_pins(source),
            ["TestA.pe_version (line 5)", "TestA.pe_version_reason (line 6)", "TestB.pe_version (line 10)"],
        )

    def test_require_names_each_offending_module(self) -> None:
        sources = {
            "a/test_a.py": "class TestA(PeIntegrationTestCase):\n    pe_version = '2.145.6'\n",
            "b/test_b.py": OVERRIDDEN,
        }

        with patch.object(Path, "read_text", lambda path: sources[str(path.relative_to(REPO_ROOT))]):
            with self.assertRaisesMessage(CommandError, "a/test_a.py: TestA.pe_version (line 2) sets") as raised:
                require_module_level_pins(list(sources))

        self.assertNotIn("b/test_b.py", str(raised.exception))

    def test_the_rewritable_layout_is_readable(self) -> None:
        self.assertEqual(unreadable_module_pins(OVERRIDDEN), [])
        self.assertEqual(unreadable_module_pins('PE_VERSION = "2.9.0"\nPE_VERSION_REASON = "held"\n'), [])

    def test_flags_module_pins_adoption_cannot_rewrite(self) -> None:
        cases = {
            'PE_VERSION: str = "2.94.7"\n': "PE_VERSION (line 1) isn't in the form",
            'PE_VERSION = "2.94.7"  # held\n': "PE_VERSION (line 1) isn't in the form",
            'PE_VERSION = "2.9.0"\nPE_VERSION_REASON: str = "held"\n': "PE_VERSION_REASON (line 2) isn't in the form",
            'PE_VERSION_REASON = "a" + "b"\n': "PE_VERSION_REASON (line 1) isn't in the form",
            "from elsewhere import PE_VERSION\n": "PE_VERSION is imported (line 1)",
            'PE_VERSION = "2.9.0"\nPE_VERSION = "2.10.0"\n': "PE_VERSION is set twice (line 2)",
            'if True:\n    PE_VERSION = "2.94.7"\n': "PE_VERSION is set inside a block (line 2)",
            "try:\n    from elsewhere import PE_VERSION_REASON\nexcept ImportError:\n    pass\n": (
                "PE_VERSION_REASON is imported inside a block (line 2)"
            ),
        }

        for source, problem in cases.items():
            with self.subTest(source=source):
                found = unreadable_module_pins(source)
                self.assertEqual(len(found), 1)
                self.assertIn(problem, found[0])

    def test_require_names_an_unreadable_module_pin(self) -> None:
        sources = {"a/test_a.py": 'PE_VERSION = "2.94.7"  # held\n'}

        with patch.object(Path, "read_text", lambda path: sources[str(path.relative_to(REPO_ROOT))]):
            with self.assertRaisesMessage(CommandError, "a/test_a.py: PE_VERSION (line 1)"):
                require_module_level_pins(list(sources))

    def test_require_passes_the_repo_as_committed(self) -> None:
        require_module_level_pins(pe_test_files())
