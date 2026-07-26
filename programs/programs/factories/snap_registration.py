"""
Real (non-test) registration of per-state SNAP calculators through
CalculatorFactory + SnapCalculator, per DECISIONS.md D-013. Same shape as
factories/tests/toy_registration.py, but not fictional and not under
tests/ -- each *SnapCalculator is a genuine candidate for Phase 4's
parallel verification against its real old calculator (co/pe/spm.py,
wa/pe/spm.py, ...). CO SNAP's parity run is human-confirmed (ROADMAP.md
Phase 4, 2026-07-13); WA is the second state, picked specifically to
prove the pattern against a real state-specific mechanism (the BBCE
net-income waiver -- confirmed to live entirely inside PolicyEngine
itself, not in WaSnap's Python, during the Phase 4 audit).

TX is the third state -- confirmed pure pass-through during the Phase 4
audit (no state-specific mechanism comparable to WA's BBCE waiver), so its
parity harness reuses the same generic scenario shapes CO's does rather
than adding a state-specific stress scenario.

NC is the fourth state. NcSnap (nc/pe/spm.py) is pure pass-through per the
Phase 4 audit, same shape as TX/WA/CO's Snap subclasses -- but NC has its
own real state-specific mechanism worth stressing: "Expanded (200%)
Categorical Eligibility" (NC FNS Manual Section 220, Change #02-2024,
2024-10-01, ncdhhs.gov), under which a household passing the 200% FPL
gross-income test is exempt from *both* the gross and net income limits
tests (Section 220.05.A.2) -- independently derived, NC's own equivalent of
WA's BBCE net-income waiver, not copied from WA's fixture/spec.

MA is the fifth state. MaSnap (ma/pe/spm.py) is pure pass-through per the
Phase 4 audit, but MA has its own real, different-shaped state-specific
mechanism: broad-based categorical eligibility (BBCE) at 200% FPL gross
income (106 CMR 364.976, "Gross Monthly Categorical Eligibility Income
Standards", mass.gov) -- but unlike WA's/NC's full gross+net waiver, MA's
BBCE raises the gross ceiling only; the net income test at 100% FPL still
applies to the general (non-elderly/disabled, non-cash-assistance)
population (Massachusetts Legal Help, "68. Is there a gross income test for
SNAP?", masslegalhelp.org). Independently researched and stress-tested
rather than assumed to generalize from WA/NC's shape.

KS is the sixth state. KsSnap (ks/pe/spm.py) is pure pass-through per the
Phase 4 audit. Kansas is confirmed one of only 7 states that has NOT
adopted BBCE at all (CBPP, "Over 40 States Use Broad-Based Categorical
Eligibility", cbpp.org/charts/over-40-states-use-broad-based-categorical-eligibility)
-- straight federal 130% FPL gross test, standard net test, standard asset
test, no state-specific mechanism comparable to WA's/NC's/MA's BBCE
variants. Same reasoning as TX: scenarios reuse the generic shapes rather
than adding a state-specific stress case.

IL is the seventh state -- the last of the original 7 audited states,
deliberately held back for this demo (not a blocker). IlSnap (il/pe/spm.py)
is pure pass-through per the Phase 4 audit, same shape as WA/TX/NC/MA/KS.
IL's own state-specific mechanism (BBCE) was researched directly against
PolicyEngine's real parameters, not a secondary source, since two secondary
sources disagreed with each other (165% vs. 200% FPL): PolicyEngine's own
`gov/hhs/tanf/non_cash/income_limit/gross.yaml` sets IL's BBCE gross
ceiling at 165% FPL (IDHS MR #15.23 / PA 099-0170), `net_applies/
non_hheod.yaml` waives the net income test for IL, and `asset_limit.yaml`
sets IL's asset limit to `.inf` (no asset test) -- a full gross+net+asset
waiver, the same shape as WA/NC/TX's BBCE, not MA's partial (gross-only)
pattern.

Deliberately not imported by co/pe/__init__.py, wa/pe/__init__.py,
tx/pe/__init__.py, nc/pe/__init__.py, ma/pe/__init__.py, ks/pe/__init__.py,
il/pe/__init__.py, or any real registry yet -- wiring this into production
orchestration is a separate, later ROADMAP checklist item.
"""

from __future__ import annotations

from django.conf import settings

from programs.programs.calculators.snap import SnapCalculator
from programs.programs.config.loader import load_config_layer_from_file
from programs.programs.factories.calculator_factory import CalculatorFactory

CONFIG_DATA_DIR = settings.BASE_DIR / "programs" / "programs" / "config" / "data"

snap_factory = CalculatorFactory()

co_snap_config = load_config_layer_from_file(
    CONFIG_DATA_DIR / "co_snap_config.json",
    federal_path=CONFIG_DATA_DIR / "snap_federal.json",
)
CoSnapCalculator = snap_factory.register("co_snap", co_snap_config, calculator_cls=SnapCalculator)

wa_snap_config = load_config_layer_from_file(
    CONFIG_DATA_DIR / "wa_snap_config.json",
    federal_path=CONFIG_DATA_DIR / "snap_federal.json",
)
WaSnapCalculator = snap_factory.register("wa_snap", wa_snap_config, calculator_cls=SnapCalculator)

tx_snap_config = load_config_layer_from_file(
    CONFIG_DATA_DIR / "tx_snap_config.json",
    federal_path=CONFIG_DATA_DIR / "snap_federal.json",
)
TxSnapCalculator = snap_factory.register("tx_snap", tx_snap_config, calculator_cls=SnapCalculator)

nc_snap_config = load_config_layer_from_file(
    CONFIG_DATA_DIR / "nc_snap_config.json",
    federal_path=CONFIG_DATA_DIR / "snap_federal.json",
)
NcSnapCalculator = snap_factory.register("nc_snap", nc_snap_config, calculator_cls=SnapCalculator)

ma_snap_config = load_config_layer_from_file(
    CONFIG_DATA_DIR / "ma_snap_config.json",
    federal_path=CONFIG_DATA_DIR / "snap_federal.json",
)
MaSnapCalculator = snap_factory.register("ma_snap", ma_snap_config, calculator_cls=SnapCalculator)

ks_snap_config = load_config_layer_from_file(
    CONFIG_DATA_DIR / "ks_snap_config.json",
    federal_path=CONFIG_DATA_DIR / "snap_federal.json",
)
KsSnapCalculator = snap_factory.register("ks_snap", ks_snap_config, calculator_cls=SnapCalculator)

il_snap_config = load_config_layer_from_file(
    CONFIG_DATA_DIR / "il_snap_config.json",
    federal_path=CONFIG_DATA_DIR / "snap_federal.json",
)
IlSnapCalculator = snap_factory.register("il_snap", il_snap_config, calculator_cls=SnapCalculator)
