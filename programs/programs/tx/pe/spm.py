import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap, Lifeline, SchoolLunch, Tanf
from programs.programs.policyengine.calculators.base import PolicyEngineSpmCalulator


class TxSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxLifeline(Lifeline):
    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxNslp(SchoolLunch):
    """
    Texas National School Lunch Program (NSLP) calculator.

    Uses PolicyEngine-calculated benefit amounts for TX-specific NSLP eligibility
    and benefit values. Inherits from federal SchoolLunch calculator and adds
    TX state code dependency.
    """

    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxTanf(Tanf):
    """
    Texas Temporary Assistance for Needy Families (TANF) calculator.

    Uses PolicyEngine-calculated benefit amounts for TX-specific TANF eligibility
    and benefit values. Inherits from federal TANF calculator and adds TX state
    code dependency and person-level income inputs.

    Income is provided at the person level (via irs_gross_income) so PolicyEngine
    can compute tx_tanf_countable_earned_income correctly — applying the $120 work
    expense deduction and 1/3 earned income disregard per § 372.409. Passing gross
    income directly as tx_tanf_countable_earned_income (the previous approach) bypassed
    these deductions and caused households with gross wages between ~$188–$402/month
    to be incorrectly denied for a family of 3 with 1 parent.
    """

    pe_name = "tx_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.TxStateCodeDependency,
        dependency.member.TaxUnitDependentDependency,
        *dependency.irs_gross_income,
    ]

    pe_outputs = [dependency.spm.TxTanf]


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
