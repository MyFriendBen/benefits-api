"""Head Start."""

from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency


class HeadStart(PolicyEngineMembersCalculator, abstract=True):
    """
    Federal Head Start (ages 3-5). Eligibility and per-child value are computed by
    PolicyEngine's ``head_start`` variable. State subclasses add their state-code
    dependency; the rest of the inputs are shared. Categorical eligibility is fed
    by the receipt contract (SSI/SNAP/TANF) plus foster care.
    """

    pe_name = "head_start"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.FosterCareDependency,
        *dependency.irs_gross_income,
        *dependency.receipt_contract,
    ]
    pe_outputs = [dependency.member.HeadStart]
