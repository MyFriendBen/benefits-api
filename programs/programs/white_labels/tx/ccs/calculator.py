"""TxCcs."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class TxCcs(PolicyEngineSpmCalulator):
    """
    Texas Child Care Services (CCS) calculator.

    CCS offers scholarships and financial assistance for child care to eligible families,
    allowing parents to work, search for employment, attend school, or participate in
    training programs. Working parents are approved for funding for 12 months, while
    parents who are seeking employment are approved for 3 months at a time.

    Uses PolicyEngine-calculated benefit amounts for TX-specific CCS eligibility
    and benefit values.
    """

    program_code = "tx_ccs"

    pe_name = "tx_ccs"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.FullTimeCollegeStudentDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.TotalHoursWorkedDependency,
        dependency.member.ChildcareAttendingDaysPerMonthDependency,
        dependency.spm.PreSubsidyChildcareExpensesDependency,
        dependency.spm.AssetsDependency,
        dependency.household.TxStateCodeDependency,
        *dependency.irs_gross_income,
        dependency.member.AlimonyIncomeDependency,
    ]
    pe_outputs = [dependency.spm.TxCcs]
