"""Measure what a PolicyEngine version does to every spec scenario, and optionally adopt it.

PolicyEngine serves only what ``current`` and ``frontier`` resolve to, so a cassette can never be
refreshed at its old pin: re-recording is always adopting a new version. This makes that a
measured step rather than a manual one:

1. **Baseline.** Replay every PolicyEngine test from its committed cassettes and capture each
   scenario's eligibility, value and error.
2. **Record.** Re-run the same tests live at the target version, writing cassettes into a
   scratch tree (``PE_CASSETTE_ROOT``) so the committed ones are never touched, and capture again.
3. **Diff.** Compare the two captures per scenario and per module, and write ``diff.json``. A
   module is unchanged only if every one of its tests passed at the target and its scenarios'
   eligibility and values match the baseline.
4. **Adopt** (``--adopt`` only). Move ``PE_TEST_VERSION`` to the target, copy in the new
   cassettes of every unchanged module, and hold every changed or erroring module at the version
   it was on by giving it a ``pe_version`` override. Held modules are left for a person to
   reconcile with their spec. Refuses to adopt when every module errored: that points at the run
   (credentials, the PolicyEngine API), not at PolicyEngine's values.

Run from the benefits-api root. Recording needs ``POLICY_ENGINE_CLIENT_ID`` and
``POLICY_ENGINE_CLIENT_SECRET`` in the environment or ``.env``, and a local Redis::

    venv/bin/python manage.py record_and_diff --target frontier --out /tmp/pe-drift/frontier
    venv/bin/python manage.py record_and_diff --target current --out /tmp/pe-drift/current \\
        --baseline /tmp/pe-drift/frontier/baseline --adopt

Each pass is a pytest subprocess, configured through the environment variables
``pe_integration.py`` and ``conftest.py`` read; nothing here touches the database.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import requests
from decouple import config
from django.core.management.base import BaseCommand, CommandError, CommandParser

from integrations.clients.policyengine.versions import ALIASES, PE_VERSIONS_URL, is_valid_version_number

REPO_ROOT = Path(__file__).resolve().parents[3]
PE_INTEGRATION = REPO_ROOT / "programs" / "programs" / "testing_fixtures" / "pe_integration.py"
CREDENTIAL_SETTINGS = ("POLICY_ENGINE_CLIENT_ID", "POLICY_ENGINE_CLIENT_SECRET")

SUITE_PIN_PATTERN = re.compile(r'^PE_TEST_VERSION = "(?P<version>[^"]+)"$', re.M)
OVERRIDE_PATTERN = re.compile(r'^PE_VERSION = "(?P<version>[^"]+)"$', re.M)

# Environment variables read by pe_integration.py and conftest.py. Spelled out rather than
# imported: pe_integration imports the test harness, which a management command shouldn't load.
ENV_CAPTURE_DIR = "PE_CAPTURE_DIR"
ENV_VERSION_OVERRIDE = "PE_VERSION_OVERRIDE"
ENV_CASSETTE_ROOT = "PE_CASSETTE_ROOT"
ENV_RECORD = "PE_RECORD"
ENV_VCR_MODE = "VCR_MODE"
# Where conftest.py::record_test_outcome writes each test's outcome, beneath a capture directory.
OUTCOMES_SUBDIR = "outcomes"

UNCHANGED = "unchanged"
CHANGED = "changed"
ERROR = "error"

# pytest's TestReport.outcome values, worst last: a test's outcome is the worst of its phases.
PASSED = "passed"
SKIPPED = "skipped"
FAILED = "failed"
TEST_OUTCOME_RANK = {PASSED: 0, SKIPPED: 1, FAILED: 2}

HOLD_REASONS = {
    CHANGED: "Values change at PolicyEngine {target}. Held here until the change is reconciled with the spec; "
    "then remove PE_VERSION and this reason and re-record.",
    ERROR: "Errors at PolicyEngine {target}. Held here until the error is fixed; "
    "then remove PE_VERSION and this reason and re-record.",
}

Outcome = dict[str, Any]


@dataclass
class Capture:
    """What one pytest pass captured, keyed by pytest node id."""

    # Each scenario's PolicyEngine outcome, from pe_integration.py::capture_result.
    scenarios: dict[str, Outcome]
    # Each test's worst phase outcome (passed, skipped or failed), from conftest.py.
    tests: dict[str, str]


def served_versions() -> dict[str, str]:
    """What PolicyEngine's ``current`` and ``frontier`` resolve to right now.

    Fetched directly rather than through versions.py's cached lookup, which can lag a promotion
    by an hour; recording at a version PolicyEngine no longer serves fails every request.
    """
    try:
        response = requests.get(PE_VERSIONS_URL, timeout=30)
        response.raise_for_status()
        versions = response.json()
    except (requests.RequestException, ValueError) as error:
        raise CommandError(f"Could not read the served PolicyEngine versions from {PE_VERSIONS_URL}: {error}")

    if not isinstance(versions, dict) or not all(isinstance(versions.get(alias), str) for alias in ALIASES):
        raise CommandError(f"Unexpected response from {PE_VERSIONS_URL}: {versions!r}")

    return {alias: versions[alias] for alias in ALIASES}


def resolve_version(target: str, served: dict[str, str]) -> str:
    """The exact version to record at for ``target``, which PolicyEngine must currently serve."""
    if target in served:
        return served[target]

    if not is_valid_version_number(target):
        raise CommandError(f"--target must be current, frontier or an exact MAJOR.MINOR.PATCH, not {target!r}")

    if target not in served.values():
        raise CommandError(
            f"PolicyEngine serves only {served}; recording at {target} would fail every request with a 422."
        )

    return target


def require_credentials() -> None:
    """Fail unless PolicyEngine credentials are set.

    Without them the harness quietly seeds a placeholder token instead of fetching a real one
    (pe_integration.py::_can_record), and every live request fails.
    """
    missing = [name for name in CREDENTIAL_SETTINGS if not config(name, default="")]
    if missing:
        raise CommandError(f"Recording needs {' and '.join(missing)} in the environment or .env")


def suite_pin() -> str:
    """The current ``PE_TEST_VERSION``."""
    match = SUITE_PIN_PATTERN.search(PE_INTEGRATION.read_text())
    if match is None:
        raise CommandError(f"PE_TEST_VERSION not found in {PE_INTEGRATION}")

    return match.group("version")


def pe_test_files() -> list[str]:
    """Every test module built on PeIntegrationTestCase, relative to the repo root.

    Requires the harness import as well as the name, so a file that only mentions the class (in a
    fixture string, say) isn't run as a PolicyEngine test module.
    """
    result = subprocess.run(
        [
            "git",
            "grep",
            "-l",
            "--all-match",
            "-e",
            "testing_fixtures.pe_integration import",
            "-e",
            "PeIntegrationTestCase",
            "--",
            "programs/**/test_*.py",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(result.stdout.split())


def run_pass(name: str, files: list[str], out_dir: Path, env_overrides: dict[str, str]) -> Path:
    """Run one pytest pass over ``files``, capturing every scenario and test; returns the capture dir.

    Test failures are expected on a recording pass (a changed value fails its assertion), so
    the exit code is not an error: each test's outcome is captured instead. pytest's output goes
    to ``<name>.log`` in ``out_dir``.
    """
    capture_dir = out_dir / name
    if capture_dir.exists():
        shutil.rmtree(capture_dir)

    env = {key: value for key, value in os.environ.items() if key not in (ENV_VERSION_OVERRIDE, ENV_CASSETTE_ROOT)}
    env.update(env_overrides)
    env[ENV_CAPTURE_DIR] = str(capture_dir)

    log_path = out_dir / f"{name}.log"
    with open(log_path, "w") as log:
        subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
            cwd=REPO_ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    return capture_dir


def _read_jsonl(directory: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for path in sorted(directory.glob("*.jsonl"))
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def load_capture(capture_dir: Path) -> Capture:
    """Every scenario and test outcome a pass captured in ``capture_dir``.

    Fails when the directory holds no test outcomes: it isn't a capture, or its pass ran no tests.
    Comparing against an empty baseline would report every scenario as changed.
    """
    tests: dict[str, str] = {}
    for record in _read_jsonl(capture_dir / OUTCOMES_SUBDIR):
        previous = tests.get(record["test"], PASSED)
        tests[record["test"]] = max(previous, record["outcome"], key=TEST_OUTCOME_RANK.__getitem__)

    if not tests:
        raise CommandError(
            f"{capture_dir} holds no test outcomes: it isn't a record_and_diff capture directory, "
            "or its pytest pass ran no tests (see the .log beside it)."
        )

    return Capture(scenarios={record["test"]: record for record in _read_jsonl(capture_dir)}, tests=tests)


def _result(outcome: Optional[Outcome]) -> Optional[tuple[Any, Any, Any]]:
    if outcome is None:
        return None

    return (outcome["eligible"], outcome["value"], outcome["error"])


def classify_scenario(
    before: Optional[Outcome],
    after: Optional[Outcome],
    before_test: Optional[str] = PASSED,
    after_test: Optional[str] = PASSED,
) -> str:
    """``unchanged``, ``changed``, or ``error`` for one test across the two passes.

    ``before``/``after`` are its captured PolicyEngine outcomes, if it reached PolicyEngine;
    ``before_test``/``after_test`` are the test's own outcomes (None if it never ran). A test
    is unchanged only if it passed at the target with the same result as the baseline: a
    failing test's recording is discarded (conftest.py::_discard_failed_recording), so its
    module can't adopt the target even when eligibility and value match.
    """
    if before_test == FAILED or after_test is None or (after is not None and after["error"]):
        return ERROR

    if after_test == FAILED:
        # Reached PolicyEngine and got an answer the test's assertions reject.
        return CHANGED if after is not None else ERROR

    if after_test == SKIPPED:
        # Nothing was recorded, which is only fine if the baseline didn't exercise it either.
        return UNCHANGED if before_test == SKIPPED else ERROR

    if after is None:
        # Passed without reaching calc_pe_program. Fine for a test that never did.
        return UNCHANGED if before is None else ERROR

    return CHANGED if _result(before) != _result(after) else UNCHANGED


def diff_captures(target: str, files: list[str], baseline: Capture, recorded: Capture) -> dict[str, Any]:
    """Per-module comparison of a replay capture against a recording capture.

    Every module in ``files`` gets an entry; one with no test outcomes at all (a collection
    error, say) is an error, so adoption holds it instead of leaving it on the moved suite pin.
    """
    modules: dict[str, dict[str, Any]] = {}

    def module_entry(name: str) -> dict[str, Any]:
        return modules.setdefault(
            name, {"status": UNCHANGED, "baseline_versions": set(), "scenario_count": 0, "scenarios": []}
        )

    for file in files:
        module_entry(file)

    tests = set(baseline.scenarios) | set(recorded.scenarios) | set(baseline.tests) | set(recorded.tests)
    for test in sorted(tests):
        module = module_entry(test.split("::")[0])
        before, after = baseline.scenarios.get(test), recorded.scenarios.get(test)
        before_test, after_test = baseline.tests.get(test), recorded.tests.get(test)
        status = classify_scenario(before, after, before_test, after_test)

        module["scenario_count"] += 1
        if before is not None:
            module["baseline_versions"].add(before["pe_version"])

        if status != UNCHANGED:
            module["scenarios"].append(
                {
                    "test": test,
                    "status": status,
                    "before": before,
                    "after": after,
                    "before_test": before_test,
                    "after_test": after_test,
                }
            )

            # ERROR outranks CHANGED for the module as a whole.
            if module["status"] != ERROR:
                module["status"] = status

    for module in modules.values():
        module["baseline_versions"] = sorted(module["baseline_versions"])
        if module["scenario_count"] == 0:
            module["status"] = ERROR

    summary = {status: 0 for status in (UNCHANGED, CHANGED, ERROR)}
    for module in modules.values():
        summary[module["status"]] += 1

    return {"target_version": target, "summary": summary, "modules": modules}


def module_classes(source: str) -> list[str]:
    """Names of the top-level classes defined in a test module."""
    return [node.name for node in ast.parse(source).body if isinstance(node, ast.ClassDef)]


def remove_override(source: str) -> str:
    """Strip a module's ``PE_VERSION`` pin, its reason, and the class attributes using them."""
    source = OVERRIDE_PATTERN.sub("", source, count=1)
    source = re.sub(r"^PE_VERSION_REASON = (\(\n(?:.*\n)*?\)|.*)\n", "", source, count=1, flags=re.M)
    source = re.sub(r"^[ \t]+pe_version = PE_VERSION\n", "", source, flags=re.M)
    source = re.sub(r"^[ \t]+pe_version_reason = PE_VERSION_REASON\n", "", source, flags=re.M)

    return source


def add_override(source: str, version: str, reason: str) -> str:
    """Pin a module to ``version`` with ``reason``, in the layout ``remove_override`` undoes.

    The constants go after the module's imports; the class attributes go at the top of the body
    of every class that subclasses PeIntegrationTestCase directly, after its docstring if any.
    """
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    insertions: list[tuple[int, str]] = []

    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    after_imports = max((node.end_lineno or node.lineno) for node in imports) if imports else 0
    insertions.append(
        (after_imports, f"\nPE_VERSION = {json.dumps(version)}\nPE_VERSION_REASON = {json.dumps(reason)}\n")
    )

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(isinstance(base, ast.Name) and base.id == "PeIntegrationTestCase" for base in node.bases):
            continue

        first = node.body[0]
        has_docstring = (
            isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
        )
        # A decorated statement's lineno is its def line, below its decorators.
        decorators = getattr(first, "decorator_list", [])
        starts_at = min([first.lineno, *(decorator.lineno for decorator in decorators)])
        anchor = first.end_lineno if has_docstring else starts_at - 1
        indent = " " * first.col_offset
        insertions.append((anchor, f"{indent}pe_version = PE_VERSION\n{indent}pe_version_reason = PE_VERSION_REASON\n"))

    for line_number, text in sorted(insertions, reverse=True):
        lines.insert(line_number, text)

    return "".join(lines)


def copy_module_cassettes(module: str, source: str, cassette_root: Path) -> None:
    """Copy a module's freshly recorded cassettes over its committed ones."""
    test_dir = Path(module).parent
    recorded_dir = cassette_root / test_dir / "cassettes"
    committed_dir = REPO_ROOT / test_dir / "cassettes"
    if not recorded_dir.exists():
        return

    committed_dir.mkdir(exist_ok=True)
    for name in module_classes(source):
        for cassette in recorded_dir.glob(f"{name}.*.yaml"):
            shutil.copyfile(cassette, committed_dir / cassette.name)


def adopt(diff: dict[str, Any], cassette_root: Path, previous_pin: str) -> dict[str, list[str]]:
    """Move the suite to the target version, keeping changed and erroring modules on what they had.

    Every rewritten source is parsed before anything is written, so a rewrite that breaks a
    module fails the command and leaves the tree untouched.
    """
    target = diff["target_version"]
    modules = diff["modules"]
    if modules and all(info["status"] == ERROR for info in modules.values()):
        raise CommandError(
            f"Every module errored at PolicyEngine {target}, which points at the run (credentials, the "
            "PolicyEngine API) rather than at PolicyEngine's values. Nothing was adopted; see recorded.log."
        )

    result: dict[str, list[str]] = {"adopted": [], "held": []}
    rewrites: dict[Path, str] = {}

    if target != previous_pin:
        rewrites[PE_INTEGRATION] = SUITE_PIN_PATTERN.sub(
            f'PE_TEST_VERSION = "{target}"', PE_INTEGRATION.read_text(), count=1
        )

    for module, info in sorted(modules.items()):
        path = REPO_ROOT / module
        source = path.read_text()
        overridden = OVERRIDE_PATTERN.search(source) is not None

        if info["status"] == UNCHANGED:
            if overridden:
                rewrites[path] = remove_override(source)
            result["adopted"].append(module)
        else:
            if not overridden and target != previous_pin:
                rewrites[path] = add_override(source, previous_pin, HOLD_REASONS[info["status"]].format(target=target))
            result["held"].append(module)

    for path, source in rewrites.items():
        try:
            ast.parse(source)
        except SyntaxError as error:
            raise CommandError(f"Rewriting {path} would break it ({error}); nothing was adopted.")

    for path, source in rewrites.items():
        path.write_text(source)

    for module in result["adopted"]:
        copy_module_cassettes(module, (REPO_ROOT / module).read_text(), cassette_root)

    if rewrites:
        formatted = subprocess.run([sys.executable, "-m", "black", "-q", *map(str, rewrites)], cwd=REPO_ROOT)
        if formatted.returncode != 0:
            raise CommandError(f"black failed on the rewritten files: {', '.join(map(str, rewrites))}")

    return result


class Command(BaseCommand):
    help = "Measure what a PolicyEngine version does to every spec scenario, and optionally adopt it."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--target", required=True, help="current, frontier, or an exact version")
        parser.add_argument("--out", required=True, type=Path, help="scratch directory for captures, logs, diff.json")
        parser.add_argument("--baseline", type=Path, help="reuse a previous run's baseline capture directory")
        parser.add_argument("--adopt", action="store_true", help="move the suite to the target (see module docstring)")

    def handle(self, *args: Any, **options: Any) -> None:
        target = resolve_version(options["target"], served_versions())
        require_credentials()
        out_dir: Path = options["out"].resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        files = pe_test_files()
        previous_pin = suite_pin()

        if options["baseline"]:
            baseline = load_capture(options["baseline"].resolve())
        else:
            self.stdout.write(f"Baseline: replaying {len(files)} modules from committed cassettes")
            baseline = load_capture(run_pass("baseline", files, out_dir, {ENV_VCR_MODE: "none"}))

        cassette_root = out_dir / "cassettes"
        if cassette_root.exists():
            shutil.rmtree(cassette_root)

        self.stdout.write(f"Record: re-running {len(files)} modules live at PolicyEngine {target}")
        recorded = load_capture(
            run_pass(
                "recorded",
                files,
                out_dir,
                {
                    ENV_RECORD: "1",
                    ENV_VCR_MODE: "once",
                    ENV_VERSION_OVERRIDE: target,
                    ENV_CASSETTE_ROOT: str(cassette_root),
                },
            )
        )

        diff = diff_captures(target, files, baseline, recorded)
        diff["suite_pin_before"] = previous_pin
        diff_path = out_dir / "diff.json"
        # Written before adopting, so a refused adoption still leaves the diff to read.
        diff_path.write_text(json.dumps(diff, indent=2) + "\n")

        if options["adopt"]:
            diff["adopt"] = adopt(diff, cassette_root, previous_pin)
            diff_path.write_text(json.dumps(diff, indent=2) + "\n")
        self.stdout.write(
            json.dumps({"target_version": target, "summary": diff["summary"], "diff": str(out_dir / "diff.json")})
        )
