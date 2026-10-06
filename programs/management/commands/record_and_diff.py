"""Measure what a PolicyEngine version does to every spec scenario, and optionally adopt it.

PolicyEngine serves only what ``current`` and ``frontier`` resolve to, so a cassette can never be
refreshed at its old pin: re-recording is always adopting a new version. This makes that a
measured step rather than a manual one:

1. **Baseline.** Replay every PolicyEngine test from its committed cassettes and capture each
   scenario's eligibility, value and error.
2. **Record.** Re-run the same tests live at the target version, writing cassettes into a
   scratch tree (``PE_CASSETTE_ROOT``) so the committed ones are never touched, and capture again.
3. **Diff.** Compare the two captures per scenario and per module, and write ``diff.json``.
4. **Adopt** (``--adopt`` only). Move ``PE_TEST_VERSION`` to the target, copy in the new
   cassettes of every module whose values didn't change, and hold every changed module at the
   version it was on by giving it a ``pe_version`` override. Changed modules are left for a person
   to reconcile with their spec.

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
import urllib.request
from pathlib import Path
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandError, CommandParser

REPO_ROOT = Path(__file__).resolve().parents[3]
PE_INTEGRATION = REPO_ROOT / "programs" / "programs" / "testing_fixtures" / "pe_integration.py"
PE_VERSIONS_URL = "https://household.api.policyengine.org/versions/us"

VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
SUITE_PIN_PATTERN = re.compile(r'^PE_TEST_VERSION = "(?P<version>[^"]+)"$', re.M)
OVERRIDE_PATTERN = re.compile(r'^PE_VERSION = "(?P<version>[^"]+)"$', re.M)

# Environment variables read by pe_integration.py and conftest.py. Spelled out rather than
# imported: pe_integration imports the test harness, which a management command shouldn't load.
ENV_CAPTURE_DIR = "PE_CAPTURE_DIR"
ENV_VERSION_OVERRIDE = "PE_VERSION_OVERRIDE"
ENV_CASSETTE_ROOT = "PE_CASSETTE_ROOT"
ENV_RECORD = "PE_RECORD"
ENV_VCR_MODE = "VCR_MODE"

UNCHANGED = "unchanged"
CHANGED = "changed"
ERROR = "error"

Outcome = dict[str, Any]


def resolve_version(target: str) -> str:
    """An exact version for ``target``, resolving the ``current``/``frontier`` aliases live."""
    if VERSION_PATTERN.match(target):
        return target

    if target not in ("current", "frontier"):
        raise CommandError(f"--target must be current, frontier or an exact MAJOR.MINOR.PATCH, not {target!r}")

    with urllib.request.urlopen(PE_VERSIONS_URL, timeout=30) as response:
        versions = json.load(response)

    return versions[target]


def suite_pin() -> str:
    """The current ``PE_TEST_VERSION``."""
    match = SUITE_PIN_PATTERN.search(PE_INTEGRATION.read_text())
    if match is None:
        raise CommandError(f"PE_TEST_VERSION not found in {PE_INTEGRATION}")

    return match.group("version")


def pe_test_files() -> list[str]:
    """Every test module built on PeIntegrationTestCase, relative to the repo root."""
    result = subprocess.run(
        ["git", "grep", "-l", "PeIntegrationTestCase", "--", "programs/**/test_*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted(result.stdout.split())


def run_pass(name: str, files: list[str], out_dir: Path, env_overrides: dict[str, str]) -> Path:
    """Run one pytest pass over ``files``, capturing every scenario; returns the capture dir.

    Test failures are expected on a recording pass (a changed value fails its assertion), so
    the exit code is not an error. pytest's output goes to ``<name>.log`` in ``out_dir``.
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

    if not capture_dir.exists():
        raise CommandError(f"The {name} pass captured nothing; see {log_path}")

    return capture_dir


def load_capture(capture_dir: Path) -> dict[str, Outcome]:
    """Every captured scenario in ``capture_dir``, keyed by pytest node id."""
    outcomes: dict[str, Outcome] = {}
    for path in sorted(capture_dir.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                record = json.loads(line)
                outcomes[record["test"]] = record

    return outcomes


def _result(outcome: Optional[Outcome]) -> Optional[tuple[Any, Any, Any]]:
    if outcome is None:
        return None

    return (outcome["eligible"], outcome["value"], outcome["error"])


def classify_scenario(before: Optional[Outcome], after: Optional[Outcome]) -> str:
    """``unchanged``, ``changed``, or ``error`` for one scenario across the two passes.

    A scenario with no outcome after recording never reached PolicyEngine, which is an error:
    something failed before the request, and there is nothing to compare.
    """
    if after is None or after["error"]:
        return ERROR

    if _result(before) != _result(after):
        return CHANGED

    return UNCHANGED


def diff_captures(target: str, baseline: dict[str, Outcome], recorded: dict[str, Outcome]) -> dict[str, Any]:
    """Per-module comparison of a replay capture against a recording capture."""
    modules: dict[str, dict[str, Any]] = {}

    for test in sorted(set(baseline) | set(recorded)):
        module = modules.setdefault(
            test.split("::")[0],
            {"status": UNCHANGED, "baseline_versions": set(), "scenario_count": 0, "scenarios": []},
        )
        before, after = baseline.get(test), recorded.get(test)
        status = classify_scenario(before, after)

        module["scenario_count"] += 1
        if before is not None:
            module["baseline_versions"].add(before["pe_version"])

        if status != UNCHANGED:
            module["scenarios"].append({"test": test, "status": status, "before": before, "after": after})

            # ERROR outranks CHANGED for the module as a whole.
            if module["status"] != ERROR:
                module["status"] = status

    for module in modules.values():
        module["baseline_versions"] = sorted(module["baseline_versions"])

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
        anchor = first.end_lineno if has_docstring else first.lineno - 1
        indent = " " * first.col_offset
        insertions.append((anchor, f"{indent}pe_version = PE_VERSION\n{indent}pe_version_reason = PE_VERSION_REASON\n"))

    for line_number, text in sorted(insertions, reverse=True):
        lines.insert(line_number, text)

    return "".join(lines)


def copy_module_cassettes(module: str, source: str, cassette_root: Path) -> int:
    """Copy a module's freshly recorded cassettes over its committed ones; returns how many."""
    test_dir = Path(module).parent
    recorded_dir = cassette_root / test_dir / "cassettes"
    committed_dir = REPO_ROOT / test_dir / "cassettes"
    if not recorded_dir.exists():
        return 0

    committed_dir.mkdir(exist_ok=True)
    copied = 0
    for name in module_classes(source):
        for cassette in recorded_dir.glob(f"{name}.*.yaml"):
            shutil.copyfile(cassette, committed_dir / cassette.name)
            copied += 1

    return copied


def adopt(diff: dict[str, Any], cassette_root: Path, previous_pin: str) -> dict[str, list[str]]:
    """Move the suite to the target version, keeping changed modules on what they had."""
    target = diff["target_version"]
    result: dict[str, list[str]] = {"adopted": [], "held": []}

    if target != previous_pin:
        PE_INTEGRATION.write_text(
            SUITE_PIN_PATTERN.sub(f'PE_TEST_VERSION = "{target}"', PE_INTEGRATION.read_text(), count=1)
        )

    for module, info in sorted(diff["modules"].items()):
        path = REPO_ROOT / module
        source = path.read_text()
        overridden = OVERRIDE_PATTERN.search(source) is not None

        if info["status"] == UNCHANGED:
            copy_module_cassettes(module, source, cassette_root)
            if overridden:
                source = remove_override(source)
            result["adopted"].append(module)
        else:
            if not overridden and target != previous_pin:
                source = add_override(
                    source,
                    previous_pin,
                    f"Values change at PolicyEngine {target}. Held here until the change is reconciled with "
                    "the spec; then remove PE_VERSION and this reason and re-record.",
                )
            result["held"].append(module)

        path.write_text(source)

    subprocess.run([sys.executable, "-m", "black", "-q", str(PE_INTEGRATION), *diff["modules"]], cwd=REPO_ROOT)

    return result


class Command(BaseCommand):
    help = "Measure what a PolicyEngine version does to every spec scenario, and optionally adopt it."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--target", required=True, help="current, frontier, or an exact version")
        parser.add_argument("--out", required=True, type=Path, help="scratch directory for captures, logs, diff.json")
        parser.add_argument("--baseline", type=Path, help="reuse a previous run's baseline capture directory")
        parser.add_argument("--adopt", action="store_true", help="move the suite to the target (see module docstring)")

    def handle(self, *args: Any, **options: Any) -> None:
        target = resolve_version(options["target"])
        out_dir: Path = options["out"].resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        files = pe_test_files()
        previous_pin = suite_pin()

        if options["baseline"]:
            baseline_dir = options["baseline"].resolve()
        else:
            self.stdout.write(f"Baseline: replaying {len(files)} modules from committed cassettes")
            baseline_dir = run_pass("baseline", files, out_dir, {ENV_VCR_MODE: "none"})

        cassette_root = out_dir / "cassettes"
        if cassette_root.exists():
            shutil.rmtree(cassette_root)

        self.stdout.write(f"Record: re-running {len(files)} modules live at PolicyEngine {target}")
        recorded_dir = run_pass(
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

        diff = diff_captures(target, load_capture(baseline_dir), load_capture(recorded_dir))
        diff["suite_pin_before"] = previous_pin

        if options["adopt"]:
            diff["adopt"] = adopt(diff, cassette_root, previous_pin)

        (out_dir / "diff.json").write_text(json.dumps(diff, indent=2) + "\n")
        self.stdout.write(
            json.dumps({"target_version": target, "summary": diff["summary"], "diff": str(out_dir / "diff.json")})
        )
