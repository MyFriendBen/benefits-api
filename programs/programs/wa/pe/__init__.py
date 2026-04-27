import programs.programs.wa.pe.member as member
from programs.programs.policyengine.calculators.base import (
    PolicyEngineCalulator,
    PolicyEngineMembersCalculator,
    PolicyEngineSpmCalulator,
    PolicyEngineTaxUnitCalulator,
)

wa_member_calculators: dict[str, type[PolicyEngineMembersCalculator]] = {
    "wa_ssi": member.WaSsi,
}

wa_tax_unit_calculators: dict[str, type[PolicyEngineTaxUnitCalulator]] = {}

wa_spm_calculators: dict[str, type[PolicyEngineSpmCalulator]] = {}

wa_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **wa_member_calculators,
    **wa_tax_unit_calculators,
    **wa_spm_calculators,
}
