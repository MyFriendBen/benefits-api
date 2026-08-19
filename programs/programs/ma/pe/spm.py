from programs.programs.federal.pe.member import Ssi
from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency
from programs.programs.cross_white_label.snap.base import Snap


class MaTafdc(PolicyEngineSpmCalulator):
    program_code = "ma_tafdc"
    pe_name = "ma_tafdc"
    pe_inputs = [
        dependency.spm.PreSubsidyChildcareExpensesDependency,
        dependency.member.MaTanfCountableGrossEarnedIncomeDependency,
        dependency.member.MaTanfCountableGrossUnearnedIncomeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.MaTotalHoursWorkedDependency,
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.MaTafdcPregnancyEligibleDependency,
        dependency.household.IsInPublicHousingDependency,
        dependency.household.MaStateCodeDependency,
    ]

    pe_outputs = [dependency.spm.MaTafdc]


class MaEaedc(PolicyEngineSpmCalulator):
    program_code = "ma_eaedc"
    pe_name = "ma_eaedc"
    pe_inputs = [
        dependency.spm.MaEaedcLivingArangementDependency,
        dependency.spm.CashAssetsDependency,
        dependency.spm.PreSubsidyChildcareExpensesDependency,
        dependency.spm.MaEaedcNonFinancialCriteria,
        dependency.member.EmploymentIncomeDependency,
        dependency.member.SelfEmploymentIncomeDependency,
        dependency.member.InvestmentIncomeDependency,
        dependency.member.PensionIncomeDependency,
        dependency.member.SocialSecurityIncomeDependency,
        dependency.member.AgeDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.MaTotalHoursWorkedDependency,
        dependency.member.IsDisabledDependency,
        *Ssi.pe_inputs,
    ]
    pe_outputs = [dependency.spm.MaEaedc]


class MaHeap(PolicyEngineSpmCalulator):
    program_code = "ma_heap"
    pe_name = "ma_liheap"

    pe_inputs = [
        dependency.household.MaStateCodeDependency,
        *dependency.irs_gross_income,
        dependency.spm.MaLiheapReceivesHousingAssistance,
        dependency.spm.MaLiheapHeatExpenseIncludedInRent,
        dependency.spm.HasHeatingCoolingExpenseDependency,
        # Final payment is min(payment_amount, heating + gas + electricity expense).
        # PE's state LIHEAP reads heating from heating_expense_person (person-level)
        # and auto-aggregates to the spm_unit total. Without this PE sees $0 of
        # heating expense and caps the benefit at $0.
        dependency.member.HeatingExpensePersonDependency,
        dependency.spm.ElectricityExpenseDependency,
    ]

    pe_outputs = [
        dependency.spm.MaLiheap,
    ]
