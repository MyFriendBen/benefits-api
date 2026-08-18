import programs.framework.pe_dependencies as dependency
from programs.programs.federal.pe.spm import Snap, Tanf


class CoSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]


class CoTanf(Tanf):
    pe_name = "co_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.CoStateCodeDependency,
        dependency.member.PregnancyDependency,
        dependency.spm.CoTanfCountableGrossIncomeDependency,
        dependency.spm.CoTanfCountableGrossUnearnedIncomeDependency,
    ]

    pe_outputs = [dependency.spm.CoTanf]
