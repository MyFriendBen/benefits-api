from programs.programs.{{code}}.pe import spm
import programs.programs.{{code}}.pe.tax as tax
import programs.programs.{{code}}.pe.member as member
import programs.programs.{{code}}.pe.spm as spm
from programs.framework.pe_base import PolicyEngineCalulator


# TODO: update /integrations/clients/policyengine/registry.py
{{code}}_member_calculators = {  # TODO: add state specific member benefits from PE
    "{{code}}_medicaid": member.{{code_capitalize}}Medicaid,
}

{{code}}_tax_unit_calculators = {}  # TODO: add state specific tax benefits from PE

{{code}}_spm_calculators = {  # TODO: add state specific SPM benefits from PE
    "{{code}}_snap": spm.{{code_capitalize}}Snap,
}

{{code}}_pe_calculators: dict[str, type[PolicyEngineCalulator]] = {
    **{{code}}_member_calculators,
    **{{code}}_tax_unit_calculators,
    **{{code}}_spm_calculators,
}
