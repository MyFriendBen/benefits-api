"""
Per-state manifest for the TANF parity harness -- same generalized shape as
snap_parity_manifest.py (DECISIONS.md D-017) from day one, not the
pre-D-017 per-state-file approach SNAP started with. Reusing D-017's
already-proven mechanism here (rather than hand-copying test_snap_parity.py
into a near-duplicate test_tanf_parity.py) is a direct application of an
already-settled pattern, not a new design decision.

**Deliberately not unified with snap_parity_manifest.py into one
cross-program harness yet.** D-017 itself only generalized *across states*
after three real per-state files (CO/WA/TX) proved the duplication was
real, not before -- generalizing speculatively from one example was exactly
what D-002/D-008 already warn against. TANF is only the second program
overall; unifying across *programs* now would be generalizing from a
single data point the same way. Revisit once a third program's parity
harness is being built, with two real examples (SNAP, TANF) to generalize
from instead of one.

TX is the first state registered -- see tanf_registration.py's docstring
for why it's the safest first pick (pure pass-through, no countable-income
override to litigate, unlike CO/IL/NC per D-020). Remaining states (no
bespoke TanfCalculator needed; MA is a real out-of-scope exception; which
other real states to add, and in what order, is a separate, later
decision).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from programs.programs.factories.tanf_registration import tanf_factory
from programs.programs.tx.pe.spm import TxTanf
from programs.programs.wa.pe.spm import WaTanf

FIXTURE_DIR = settings.BASE_DIR / "validations" / "management" / "commands" / "import_validations" / "data"


@dataclass(frozen=True)
class TanfParityState:
    state_code: str  # "co" -- WhiteLabel.code, Program white_label
    state_name: str  # "Colorado" -- WhiteLabel.name
    postal_code: str  # "CO" -- WhiteLabel.state_code
    old_calculator_cls: type
    new_calculator_key: str  # tanf_factory registration key, e.g. "co_tanf"

    @property
    def fixture_path(self) -> Path:
        return FIXTURE_DIR / f"{self.state_code}_tanf.json"


TANF_PARITY_STATES: list[TanfParityState] = [
    TanfParityState(
        state_code="tx",
        state_name="Texas",
        postal_code="TX",
        old_calculator_cls=TxTanf,
        new_calculator_key="tx_tanf",
    ),
    TanfParityState(
        state_code="wa",
        state_name="Washington",
        postal_code="WA",
        old_calculator_cls=WaTanf,
        new_calculator_key="wa_tanf",
    ),
]


def build_tanf_parity_cases() -> tuple[list[tuple[TanfParityState, dict]], list[str]]:
    """Identical mechanism to build_snap_parity_cases() -- see
    snap_parity_manifest.py's docstring for the full reasoning (fixture is
    the sole source of scenario truth; every failure mode raises loudly at
    module-import time). Returns ([], []) with zero states registered,
    which pytest.mark.parametrize collects as zero test cases, not an
    error -- confirmed before treating this scaffold as done."""
    cases: list[tuple[TanfParityState, dict]] = []
    ids: list[str] = []

    for entry in TANF_PARITY_STATES:
        try:
            tanf_factory.get(entry.new_calculator_key)
        except KeyError:
            raise AssertionError(
                f"{entry.state_code}: '{entry.new_calculator_key}' is not registered in "
                f"tanf_factory (available: {sorted(tanf_factory.as_dict())}) -- "
                "tanf_registration.py wiring is stale or this manifest entry has a typo."
            )

        if not entry.fixture_path.exists():
            raise AssertionError(f"{entry.state_code}: fixture file not found: {entry.fixture_path}")

        raw_scenarios = json.loads(entry.fixture_path.read_text())
        if not raw_scenarios:
            raise AssertionError(f"{entry.state_code}: {entry.fixture_path} has zero scenarios")

        seen_keys: set[str] = set()
        for raw in raw_scenarios:
            key = raw["scenario_key"]
            if key in seen_keys:
                raise AssertionError(f"{entry.state_code}: duplicate scenario_key {key!r} in {entry.fixture_path}")
            seen_keys.add(key)
            cases.append((entry, raw))
            ids.append(f"{entry.state_code}-{key}")

    return cases, ids
