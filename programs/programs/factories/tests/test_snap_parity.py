"""
SNAP parallel-verification harness (ROADMAP.md Phase 4, DECISIONS.md D-017):
compares each state's real old calculator (CoSnap/WaSnap/TxSnap, ...)
against the new SnapCalculator (programs/programs/calculators/snap.py,
D-013) household values for the same real households, for every state and
scenario in snap_parity_manifest.py.

Generalizes what used to be three separate, ~95%-identical hand-copied test
files (one per state) into a single parameterized mechanism -- see
snap_parity_manifest.py's docstring for why the manifest itself can't be
pure JSON, and DECISIONS.md D-017 for the full ADR (ids as "state-scenario_key"
make cross-state VCR cassette collision, D-016's bug, structurally
impossible rather than a naming convention to remember; the fixture file is
the sole source of truth for which scenarios exist, so there's no separate
expected-count list to keep in sync, D-015's original concern).

Calls the real calc_pe_eligibility() entry point directly (not a hand-rolled
pe_input()/all_eligibility() reimplementation) -- reproduces its own
can_calc() gate for free and guarantees both calculators share exactly one
already-constructed Sim (D-014's precondition). pe_engines is patched to
[DockerApiSim] for the duration of each test, per D-003 (DockerApiSim is
policyengine/tests/test_integration.py's own definition, imported rather
than redefined a fourth time).

resolve_unpinned_comparable_version is mocked to a fixed, cited constant
(D-017 point 3) -- SNAP's SnapJobTrainingStudentDependency is version-gated
(min_pe_version=(1,752,0)), so every SNAP request triggers a live,
uncached-per-process call to PolicyEngine's real hosted /versions/us
endpoint when unmocked. That call caused a real, confirmed transient
failure while recording TX's cassettes (RISKS.md Phase 4). Mocking to a
fixed version clears that floor deterministically without changing which
inputs get sent (verified against all three states' pre-refactor,
already-recorded cassette bodies -- see D-017).

Run: pytest -m integration programs/programs/factories/tests/test_snap_parity.py
"""

from unittest.mock import patch

import pytest

from programs.models import FederalPoveryLimit, Program
from programs.programs.factories.snap_registration import snap_factory
from programs.programs.factories.tests.snap_parity_manifest import (
    SnapParityState,
    build_snap_parity_cases,
)
from programs.programs.policyengine.policy_engine import calc_pe_eligibility
from programs.programs.policyengine.tests.test_integration import DockerApiSim
from screener.models import WhiteLabel
from screener.serializers import ScreenSerializer

SNAP_PARITY_CASES, SNAP_PARITY_IDS = build_snap_parity_cases()

# PolicyEngine's actual resolved "current" at CO's original recording time
# (from that cassette's recorded /versions/us response: {"current":"1.755.0", ...}).
# Clears SnapJobTrainingStudentDependency's (1, 752, 0) floor, matching what
# CO/WA/TX's already-recorded, already-reviewed cassettes actually sent (D-017).
RESOLVED_COMPARABLE_VERSION = (1, 755, 0)


@pytest.fixture(autouse=True)
def _mock_pe_version_resolution():
    with patch(
        "programs.programs.policyengine.policy_engine.pe_versions.resolve_unpinned_comparable_version",
        return_value=RESOLVED_COMPARABLE_VERSION,
    ):
        yield


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.parametrize("case", SNAP_PARITY_CASES, ids=SNAP_PARITY_IDS)
def test_snap_parity(case: tuple[SnapParityState, dict]):
    entry, raw = case
    scenario_key = raw["scenario_key"]
    notes = raw["notes"]

    fpl_year = FederalPoveryLimit.objects.create(year="2024", period="2024")
    WhiteLabel.objects.create(name=entry.state_name, code=entry.state_code, state_code=entry.postal_code)

    screen = ScreenSerializer(data={**raw["household"], "is_test": True})
    screen.is_valid(raise_exception=True)
    screen = screen.save()

    program_key = entry.new_calculator_key
    program = Program.objects.new_program(white_label=entry.state_code, name_abbreviated=program_key)
    program.year = fpl_year
    program.save()

    missing_dependencies = screen.missing_fields()

    old_calc = entry.old_calculator_cls(screen, program, missing_dependencies)
    new_calc = snap_factory.get(program_key)(screen, program, missing_dependencies)

    old_key = program_key
    new_key = f"{program_key}_new"

    with patch("programs.programs.policyengine.policy_engine.pe_engines", [DockerApiSim]):
        result = calc_pe_eligibility(screen, {old_key: old_calc, new_key: new_calc})

    eligibility = result["eligibility"]

    if not eligibility:
        pytest.fail(
            f"[{entry.state_code}:{scenario_key}] {notes}\n"
            "calc_pe_eligibility() returned no eligibility results at all for either "
            "calculator -- most likely the PolicyEngine Docker container is unreachable "
            "(calc_pe_eligibility swallows the underlying exception and returns an empty "
            "result rather than raising). Confirm the container is running before treating "
            "this as a real parity mismatch."
        )

    missing_sides = {old_key, new_key} - eligibility.keys()
    if missing_sides:
        pytest.fail(
            f"[{entry.state_code}:{scenario_key}] {notes}\n"
            f"can_calc()-divergence: {sorted(missing_sides)} missing from calc_pe_eligibility()'s "
            f"result (old_calc.can_calc()={old_calc.can_calc()}, "
            f"new_calc.can_calc()={new_calc.can_calc()}). old and new must agree on whether "
            "they have enough data to calculate at all, not just on the resulting value."
        )

    old_eligibility = eligibility[old_key]
    new_eligibility = eligibility[new_key]

    print(
        f"[{entry.state_code}:{scenario_key}] household_value -- "
        f"old ({entry.old_calculator_cls.__name__})={old_eligibility.household_value} "
        f"new (ConfigurableCalculator)={new_eligibility.household_value}"
    )

    if old_eligibility.eligible != new_eligibility.eligible:
        pytest.fail(
            f"[{entry.state_code}:{scenario_key}] {notes}\n"
            f"eligibility-boolean mismatch: old={old_eligibility.eligible} "
            f"new={new_eligibility.eligible}"
        )

    if old_eligibility.household_value != new_eligibility.household_value:
        pytest.fail(
            f"[{entry.state_code}:{scenario_key}] {notes}\n"
            f"dollar-value mismatch (D-014 exact match, no tolerance): "
            f"old={old_eligibility.household_value} new={new_eligibility.household_value}"
        )
