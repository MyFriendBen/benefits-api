"""
Per-state manifest for the SNAP parity harness (DECISIONS.md D-017).
Generalizes what used to be three hand-copied test files
(test_snap_parity.py/test_wa_snap_parity.py/test_tx_snap_parity.py) into one
parameterized mechanism -- see test_snap_parity.py for the test itself.

Not pure JSON: each state's *old* calculator (CoSnap/WaSnap/TxSnap, ...) is a
real Python class in a per-state module, and JSON cannot reference one.
Adding a state to this harness is one SnapParityState entry (an import + a
few lines) plus the real fixture-authoring work in
validations/management/commands/import_validations/data/{state}_snap.json --
not zero Python. This is separate from, and in addition to,
snap_registration.py's pre-existing one-line *production* registration for
the new calculator (D-013).

D-001's rejection of auto-discovery for the production CalculatorFactory
applies here too: an importlib-convention lookup
(programs.programs.{state}.pe.spm.{State}Snap) would make this file closer
to real JSON, but fails at an unhelpful runtime AttributeError instead of a
known import line if a future state's class doesn't follow the convention,
and buys nothing against the loud-failure requirement below, which an
explicit registry gets from a plain ImportError/AssertionError for free.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from programs.programs.co.pe.spm import CoSnap
from programs.programs.factories.snap_registration import snap_factory
from programs.programs.il.pe.spm import IlSnap
from programs.programs.ks.pe.spm import KsSnap
from programs.programs.ma.pe.spm import MaSnap
from programs.programs.nc.pe.spm import NcSnap
from programs.programs.tx.pe.spm import TxSnap
from programs.programs.wa.pe.spm import WaSnap

FIXTURE_DIR = settings.BASE_DIR / "validations" / "management" / "commands" / "import_validations" / "data"


@dataclass(frozen=True)
class SnapParityState:
    state_code: str  # "co" -- WhiteLabel.code, Program white_label
    state_name: str  # "Colorado" -- WhiteLabel.name
    postal_code: str  # "CO" -- WhiteLabel.state_code
    old_calculator_cls: type
    new_calculator_key: str  # snap_factory registration key, e.g. "co_snap"

    @property
    def fixture_path(self) -> Path:
        return FIXTURE_DIR / f"{self.state_code}_snap.json"


SNAP_PARITY_STATES: list[SnapParityState] = [
    SnapParityState("co", "Colorado", "CO", CoSnap, "co_snap"),
    SnapParityState("wa", "Washington", "WA", WaSnap, "wa_snap"),
    SnapParityState("tx", "Texas", "TX", TxSnap, "tx_snap"),
    SnapParityState("nc", "North Carolina", "NC", NcSnap, "nc_snap"),
    SnapParityState("ma", "Massachusetts", "MA", MaSnap, "ma_snap"),
    SnapParityState("ks", "Kansas", "KS", KsSnap, "ks_snap"),
    SnapParityState("il", "Illinois", "IL", IlSnap, "il_snap"),
]


def build_snap_parity_cases() -> tuple[list[tuple[SnapParityState, dict]], list[str]]:
    """One (state, raw_scenario_dict) case per scenario found in each state's
    real fixture file -- the fixture is the sole source of truth for which
    scenarios exist, so there's no separate list to fall out of sync with it
    (D-015's original concern, now structurally impossible instead of
    hand-maintained). Every failure mode here raises loudly at call time
    (test_snap_parity.py calls this at module-import time, so a bad manifest
    entry fails collection for the whole file) rather than silently
    producing zero cases for a state."""
    cases: list[tuple[SnapParityState, dict]] = []
    ids: list[str] = []

    for entry in SNAP_PARITY_STATES:
        try:
            snap_factory.get(entry.new_calculator_key)
        except KeyError:
            raise AssertionError(
                f"{entry.state_code}: '{entry.new_calculator_key}' is not registered in "
                f"snap_factory (available: {sorted(snap_factory.as_dict())}) -- "
                "snap_registration.py wiring is stale or this manifest entry has a typo."
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
