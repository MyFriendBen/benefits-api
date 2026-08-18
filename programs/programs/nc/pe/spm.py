import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineSpmCalulator
from programs.programs.federal.pe.spm import Snap, Tanf


class NcSnap(Snap):
    program_code = "nc_snap"
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]


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
