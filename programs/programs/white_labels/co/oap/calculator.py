"""OldAgePension."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class OldAgePension(PolicyEngineMembersCalculator):
    program_code = "oap"
    pe_name = "co_oap"
    pe_inputs = [
        dependency.member.SsiCountableResourcesDependency,
        dependency.member.SsiEarnedIncomeDependency,
        dependency.member.SsiUnearnedIncomeDependency,
        dependency.member.AgeDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.member.Oap]
