"""Tests for the pure parts of record_and_diff: the scenario diff and the override rewrite."""

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
    classify_scenario,
    diff_captures,
    format_rewrite,
    load_capture,
    module_classes,
    remove_override,
    resolve_version,
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

    pe_version = PE_VERSION
    pe_version_reason = PE_VERSION_REASON

    def test_one(self):
        pass


class TestB(PeIntegrationTestCase):
    pe_version = PE_VERSION
    pe_version_reason = PE_VERSION_REASON
    screen_id = 1
'''


class TestOverrideRewrite(SimpleTestCase):
    def test_remove_strips_the_pin_reason_and_class_attributes(self) -> None:
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
        self.assertEqual(pinned.count("    pe_version = PE_VERSION\n"), 2)
        self.assertEqual(pinned.count("    pe_version_reason = PE_VERSION_REASON\n"), 2)
        # The docstring stays the first statement of the class.
        class_a = next(node for node in ast.parse(pinned).body if getattr(node, "name", "") == "TestA")
        self.assertEqual(ast.get_docstring(class_a), "Class docstring.")
        self.assertNotIn("PE_VERSION", remove_override(pinned))

    def test_add_puts_attributes_above_a_decorated_first_method(self) -> None:
        source = (
            "from harness import PeIntegrationTestCase\n"
            "from unittest.mock import patch\n\n\n"
            "class TestA(PeIntegrationTestCase):\n"
            "    @patch('x.y')\n"
            "    def test_one(self, y):\n"
            "        pass\n"
        )

        pinned = add_override(source, "2.9.0", "held for review")

        ast.parse(pinned)
        self.assertIn("    pe_version_reason = PE_VERSION_REASON\n    @patch('x.y')\n    def test_one", pinned)

    def test_module_classes(self) -> None:
        self.assertEqual(module_classes(OVERRIDDEN), ["TestA", "TestB"])
