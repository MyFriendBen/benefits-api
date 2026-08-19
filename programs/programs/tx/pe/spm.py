import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineSpmCalulator
from programs.programs.cross_white_label.lifeline.base import Lifeline
from programs.programs.cross_white_label.nslp.base import SchoolLunch
from programs.programs.cross_white_label.snap.base import Snap
from programs.programs.cross_white_label.tanf.base import Tanf


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


class TxCeap(PolicyEngineSpmCalulator):
    """
    Texas Comprehensive Energy Assistance Program (CEAP) — the state's LIHEAP
    implementation. Helps low-income Texas households pay home heating and cooling
    costs. Households are eligible at or below 150% FPL, or categorically via
    TANF/SNAP/SSI receipt (42 U.S.C. § 8624(b)(2)(A)). The benefit is a tiered
    annual utility-assistance amount (1,800 / 1,500 / 1,200 by FPG bracket per
    10 TAC § 6.309(e)), capped by the household's reported energy expenses.
    """

    program_code = "tx_liheap"

    pe_name = "tx_ceap"
    pe_inputs = [
        dependency.household.TxStateCodeDependency,
        *dependency.irs_gross_income,
        # tx_ceap counts SSI via applicable_ssi, which follows the `ssi` input: the
        # household's reported amount where they report one, and PolicyEngine's own
        # simulated SSI otherwise. The take-up flag suppresses that simulated value for
        # anyone reporting no SSI, keeping a modelled benefit out of their FPG tier.
        *dependency.receipt_contract,
        # tx_ceap caps the payment at electricity_expense + gas_expense; route the
        # screener's energy expenses into electricity_expense so the cap is non-zero.
        dependency.spm.TxCeapEnergyExpenseDependency,
    ]
    pe_outputs = [dependency.spm.TxCeap]
