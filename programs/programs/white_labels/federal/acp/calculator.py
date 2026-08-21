"""Acp."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class Acp(PolicyEngineSpmCalulator):
    program_code = "acp"
    pe_name = "acp"
    pe_inputs = [
        dependency.spm.BroadbandCostDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.spm.Acp]
