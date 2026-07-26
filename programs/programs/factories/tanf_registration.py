"""
Real (non-test) registration of per-state TANF calculators through
CalculatorFactory, mirroring snap_registration.py's shape (D-013) with one
real difference: **no bespoke TanfCalculator subclass exists, or is needed**.

Verified directly, not assumed: federal `Tanf` (federal/pe/spm.py) does not
override `household_value()`/`pe_output_period` the way `Snap` does, and
none of the five existing state `XTanf(Tanf)` subclasses (CO/IL/NC/TX/WA)
override it either -- every one of them relies on the plain default
`PolicyEngineCalulator.household_value()` (`return int(self.get_variable())`,
reading at the calculator's configured period, no monthly output-period
split). `ConfigurableCalculator.household_value()`'s own default (Phase 3)
already does the equivalent thing (`self.client.get_spm_value(self.config.
pe_name)`, no period override, defaulting to `self.period`) -- confirmed by
directly comparing both implementations side by side, not by running
anything. So states register straight against `ConfigurableCalculator`
(the `CalculatorFactory.register()` default), no `calculator_cls=` needed.

MA is a real, separate exception, not a hidden gap in this pattern: MA's
real cash-assistance programs (`MaTafdc`/`MaEaedc`, ma/pe/spm.py) are their
own distinct PolicyEngine variables (`ma_tafdc`/`ma_eaedc`), not the
`{state}_tanf` shape federal `Tanf` composes -- confirmed against
PolicyEngine's own `gov/hhs/tanf/cash/tanf.py` dispatch list, which buckets
`ma_tafdc` under "non-standard program names," not the standard `{st}_tanf`
bucket CO/IL/NC/TX/WA (and Kansas's real `ks_tanf`) fall into. MA is
deliberately out of scope for this generic architecture; it would need its
own top-level (non-`extends`) config entries if ever added.

KS has no TANF calculator in this codebase, or in real upstream
MyFriendBen/benefits-api, at all today (checked directly) -- but
PolicyEngine's own `ks_tanf` variable is a complete, real implementation in
the standard `{st}_tanf` bucket, with genuine county-group-based payment
tiers and KS-specific income-counting rules (KEESM 4113/5110, K.A.R.
30-4-101). Adding KS is a separate, later decision, deliberately not acted
on here -- unlike TX below, KS has no existing calculator to build a
parity check against at all, so it isn't the easiest next state to confirm
this architecture with.

TX is the first real state registered here. TxTanf (tx/pe/spm.py) is a
pure pass-through -- unlike CO/IL/NC's already-flagged countable-income
override (D-020, RISKS.md), TxTanf supplies raw per-person income
(irs_gross_income) and a dependents flag, and lets PolicyEngine's own
tx_tanf formula compute the deductions/disregards itself (checked
directly, not assumed -- confirmed by direct reading, not by copying the
CO/IL/NC pattern). That makes it the safest first state to confirm this
architecture against: nothing here should diverge, so a parity pass is a
real (not merely lucky) confirmation, same discipline as D-017 checking
each SNAP state directly rather than assuming precedent generalizes.

WA is the second state registered here (D-022 -- swapped in for the
original CO demo pick, since CO's shipped calculator carries D-020's
countable-income divergence and would fail parity today, an expected
mismatch rather than a real confirmation). WaTanf (wa/pe/spm.py) is
confirmed pure pass-through the same way TxTanf is: the class defines only
pe_name/pe_inputs/pe_outputs, zero method overrides (no household_value()
override, no can_calc() override) -- checked directly, not assumed from
its spec.md's prose describing "the calculator implements this in full,"
which describes PolicyEngine's own wa_tanf formula's behavior, not custom
Python in this codebase. WaTanf's pe_inputs list is simply longer than
TxTanf's (PregnancyDependency, EmploymentIncomeBeforeLsrDependency,
SelfEmploymentIncomeBeforeLsrDependency, SocialSecurityIncomeDependency,
UnemploymentIncomeDependency, CashAssetsDependency,
WaShowAllCashAssistanceProgramsDependency) because wa_tanf's real PE
formula needs more inputs than tx_tanf's does -- more inputs, not more
logic. `dependency.spm.WaTanf` (the output dependency WaTanf reads) is
itself trivial (`field = "wa_tanf"`, no value() override), confirming the
generic output derivation `build_output_dependency()` already produces is
equivalent.

Deliberately not imported by any real state's pe/__init__.py yet -- same
deferred-wiring posture as snap_registration.py (D-013).
"""

from __future__ import annotations

from django.conf import settings

from programs.programs.config.loader import load_config_layer_from_file
from programs.programs.factories.calculator_factory import CalculatorFactory

CONFIG_DATA_DIR = settings.BASE_DIR / "programs" / "programs" / "config" / "data"

tanf_factory = CalculatorFactory()

# Loaded standalone (no federal_path -- this *is* the federal config, same
# call shape config/tests/test_loader.py already uses for snap_federal.json)
# purely so a malformed tanf_federal.json fails loud at import time, before
# any real state tries to extend it.
tanf_federal_config = load_config_layer_from_file(CONFIG_DATA_DIR / "tanf_federal.json")

tx_tanf_config = load_config_layer_from_file(
    CONFIG_DATA_DIR / "tx_tanf_config.json",
    federal_path=CONFIG_DATA_DIR / "tanf_federal.json",
)
TxTanfCalculator = tanf_factory.register("tx_tanf", tx_tanf_config)

wa_tanf_config = load_config_layer_from_file(
    CONFIG_DATA_DIR / "wa_tanf_config.json",
    federal_path=CONFIG_DATA_DIR / "tanf_federal.json",
)
WaTanfCalculator = tanf_factory.register("wa_tanf", wa_tanf_config)

# Remaining states (KS, or CO/IL/NC once D-020's discrepancy question is
# resolved) are a separate, later decision -- see module docstring. A
# future state adds:
#
#   xx_tanf_config = load_config_layer_from_file(
#       CONFIG_DATA_DIR / "xx_tanf_config.json",
#       federal_path=CONFIG_DATA_DIR / "tanf_federal.json",
#   )
#   XxTanfCalculator = tanf_factory.register("xx_tanf", xx_tanf_config)
