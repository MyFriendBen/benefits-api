import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.member import Ssi


class WaSsi(Ssi):
    """
    Washington Supplemental Security Income — federal SSI applied to WA residents.

    A thin wrapper around the federal `Ssi` PolicyEngine calculator that adds the
    WA state code so PolicyEngine can apply state-specific SSI rules. Washington
    pays no general SSI state supplement (a small supplement exists for narrow
    residential-care categories that are out of scope for the screener), so the
    output is the federal Federal Benefit Rate (FBR) — $994/mo individual,
    $1,491/mo couple for 2026 — minus PolicyEngine's countable income.

    All eligibility math (categorical entry: aged / disabled / blind, the
    $20 + $65 + 1/2 income exclusion stack, SGA cutoff, in-kind support and
    maintenance reductions, spousal and parental deeming, resource limits)
    is handled by PolicyEngine. The screener contributes only:
      - the per-member SSI input dependencies inherited from `Ssi.pe_inputs`
      - the WA state code so PE knows which state to model

    Duplicate-enrollment filtering ("not already receiving SSI") is enforced
    one layer up via `Screen.has_benefit("wa_ssi")` -> `_build_benefit_map`,
    matching the existing `ssi` and `tx_ssi` mapping.

    See `programs/programs/wa/ssi/spec.md` for the full eligibility criteria,
    PolicyEngine variable mapping, and the 15 reference test scenarios.
    """

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
