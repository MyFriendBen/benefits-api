"""NC TANF."""

from programs.programs.cross_white_label.tanf.base import Tanf
import programs.framework.pe_dependencies as dependency


class NcTanf(Tanf):
    program_code = "nc_tanf"
    pe_name = "nc_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.NcStateCodeDependency,
        dependency.spm.NcTanfCountableEarnedIncomeDependency,
        dependency.spm.NcTanfCountableGrossUnearnedIncomeDependency,
    ]

    pe_outputs = [dependency.spm.NcTanf]
