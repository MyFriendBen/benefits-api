from programs.programs.federal.pe.member import Ssi
from programs.programs.policyengine.calculators.base import PolicyEngineSpmCalulator
import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap


class MaSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.MaStateCodeDependency,
    ]


class MaTafdc(PolicyEngineSpmCalulator):
    pe_name = "ma_tafdc"
    pe_inputs = [
        dependency.spm.PreSubsidyChildcareExpensesDependency,
        dependency.member.MaTanfCountableGrossEarnedIncomeDependency,
        dependency.member.MaTanfCountableGrossUnearnedIncomeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.member.MaTotalHoursWorkedDependency,
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.household.IsInPublicHousingDependency,
        dependency.household.MaStateCodeDependency,
    ]

    pe_outputs = [dependency.spm.MaTafdc]


class MaEaedc(PolicyEngineSpmCalulator):
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
