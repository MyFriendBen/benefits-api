import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineSpmCalulator
from programs.programs.cross_white_label.snap.base import Snap
from programs.programs.cross_white_label.tanf.base import Tanf


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
