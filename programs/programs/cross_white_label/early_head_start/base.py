"""Early Head Start."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class EarlyHeadStart(PolicyEngineMembersCalculator, abstract=True):
    """
    Federal Early Head Start (birth to age 3, and pregnant women). Same computed
    eligibility/value model as ``HeadStart`` via PolicyEngine's ``early_head_start``
    variable, plus a pregnancy input (EHS serves pregnant women). State subclasses
    add their state-code dependency.
    """

    pe_name = "early_head_start"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.FosterCareDependency,
        *dependency.irs_gross_income,
        *dependency.receipt_contract,
    ]
    pe_outputs = [dependency.member.EarlyHeadStart]
