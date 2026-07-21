"""
TANF parallel-verification harness -- same mechanism as
test_snap_parity.py (ROADMAP.md Phase 4, DECISIONS.md D-017), reused
directly for TANF rather than hand-copied and adapted, since the
comparison logic itself (D-014's three-category check: can_calc()
divergence, eligibility-boolean divergence, exact dollar-value match) is
already fully generic -- nothing about it is SNAP-specific. See
tanf_parity_manifest.py's docstring for why this stays a separate file
from test_snap_parity.py rather than unifying the two into one
cross-program harness (not yet -- only the second program, same
wait-for-real-evidence reasoning D-017 itself used across states).

Unlike test_snap_parity.py, states register directly against the generic
ConfigurableCalculator, not a bespoke *Calculator subclass -- see
tanf_registration.py's docstring for the direct code-comparison proof that
none is needed.

resolve_unpinned_comparable_version is mocked here too, precautionarily --
federal Tanf's own two inputs (AgeDependency, FullTimeCollegeStudentDependency)
are not version-gated today (checked directly), so this mock isn't yet
proven necessary the way it was for SNAP's SnapJobTrainingStudentDependency.
Included anyway since it costs nothing against zero currently-registered
states and removes a known class of flakiness (RISKS.md Phase 4) for
whichever future state's dependencies turn out to be version-gated --
re-verify against that state's actual request body before trusting it,
exactly as D-017 did for SNAP, not assumed safe by analogy alone.

Run: pytest -m integration programs/programs/factories/tests/test_tanf_parity.py
"""

from unittest.mock import patch

import pytest

from programs.models import FederalPoveryLimit, Program
from programs.programs.factories.tanf_registration import tanf_factory
from programs.programs.factories.tests.tanf_parity_manifest import (
    TanfParityState,
    build_tanf_parity_cases,
)
from programs.programs.policyengine.policy_engine import calc_pe_eligibility
from programs.programs.policyengine.tests.test_integration import DockerApiSim
from screener.models import WhiteLabel
from screener.serializers import ScreenSerializer

TANF_PARITY_CASES, TANF_PARITY_IDS = build_tanf_parity_cases()

# Same cited constant as test_snap_parity.py (D-017) -- PolicyEngine's actual
# resolved "current" at CO SNAP's original recording time. Reused for
# consistency; re-verify against a real recorded /versions/us response if
# this ever needs to change independently of SNAP's value.
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
@pytest.mark.parametrize("case", TANF_PARITY_CASES, ids=TANF_PARITY_IDS)
def test_tanf_parity(case: tuple[TanfParityState, dict]):
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
    new_calc = tanf_factory.get(program_key)(screen, program, missing_dependencies)

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
