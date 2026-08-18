import programs.framework.pe_dependencies as dependency
from programs.programs.federal.pe.member import Medicaid


# TODO: add state specific Member calculators from PE here
# TODO: add dependency.household.{{code_capitalize}}StateCode dependency

# NOTE: here is a possible implentation of Medicaid for {{name}}
class {{code_capitalize}}Medicaid(Medicaid):
    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.{{code_capitalize}}StateCode,
    ]

    medicaid_categories = {  # TODO: add state specific values
        "NONE": 0,
        "ADULT": 0,
        "INFANT": 0,
        "YOUNG_CHILD": 0,
        "OLDER_CHILD": 0,
        "PREGNANT": 0,
        "YOUNG_ADULT": 0,
        "PARENT": 0,
        "SSI_RECIPIENT": 0,
        "AGED": 0,
        "DISABLED": 0,
    }
