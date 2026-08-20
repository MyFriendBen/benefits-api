"""NcScca."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class NcScca(PolicyEngineSpmCalulator):
    program_code = "nc_scca"
    pe_name = "nc_scca_maximum_payment"
    pe_inputs = [
        dependency.household.NcStateCodeDependency,
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.spm.NcSccaCountableIncomeDependency,
        dependency.household.NcCountyDependency,
    ]

    pe_outputs = [dependency.spm.NcScca]
