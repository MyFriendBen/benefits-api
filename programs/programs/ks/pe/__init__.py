import programs.programs.ks.pe.tax as tax
from programs.programs.policyengine.calculators.base import PolicyEngineCalulator

ks_tax_unit_calculators = {
    "ks_cdcc": tax.KsCdcc,
}

ks_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **ks_tax_unit_calculators,
}
