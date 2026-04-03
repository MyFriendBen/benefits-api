import programs.programs.wa.pe.spm as spm
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

wa_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    "wa_snap": spm.WaSnap,
}
