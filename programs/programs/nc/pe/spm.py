import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.policyengine.calculators.base import PolicyEngineSpmCalulator
from programs.programs.federal.pe.spm import Snap, Tanf


class NcSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.NcStateCodeDependency,
    ]


class NcTanf(Tanf):
    pe_name = "nc_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.NcStateCodeDependency,
        dependency.spm.NcTanfCountableEarnedIncomeDependency,
        dependency.spm.NcTanfCountableGrossUnearnedIncomeDependency,
    ]

    pe_outputs = [dependency.spm.NcTanf]


class NcScca(PolicyEngineSpmCalulator):
    pe_name = "nc_scca_maximum_payment"
    pe_inputs = [
        dependency.household.NcStateCodeDependency,
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.spm.NcSccaCountableIncomeDependency,
        dependency.household.NcCountyDependency,
    ]

    pe_outputs = [dependency.spm.NcScca]
