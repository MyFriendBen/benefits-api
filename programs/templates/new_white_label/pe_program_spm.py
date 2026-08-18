import programs.framework.pe_dependencies as dependency
from programs.programs.federal.pe.spm import Snap


# TODO: add state specific SPM calculators from PE here
# TODO: add dependency.household.{{code_capitalize}}StateCode dependency

# NOTE: here is a possible implentation of SNAP for {{name}}
class {{code_capitalize}}Snap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.{{code_capitalize}}StateCode,
    ]
