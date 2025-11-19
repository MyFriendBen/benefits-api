from programs.programs.federal.pe.member import Ssi
from programs.programs.policyengine.calculators.base import PolicyEngineSpmCalulator
import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap
import logging

logger = logging.getLogger(__name__)


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


class MaHeap(PolicyEngineSpmCalulator):
    pe_name = "ma_liheap"

    pe_inputs = [
        dependency.household.MaStateCodeDependency,
        *dependency.irs_gross_income,
        dependency.spm.MaLiheapReceivesHousingAssistance,
        dependency.spm.MaLiheapHeatExpenseIncludedInRent,
        dependency.spm.HasHeatingCoolingExpenseDependency,
    ]

    pe_outputs = [
        dependency.spm.MaLiheap,
    ]

    def household_value(self) -> int:
        if self.screen.has_benefit("ma_heap"):
            return 0

        try:
            payment = self.get_variable()
        except KeyError as e:
            logger.warning(f"PolicyEngine missing expected key for MA HEAP screen {self.screen.id}: {e}")
            return 0
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning(f"Error calculating MA HEAP for screen {self.screen.id}: {type(e).__name__}: {e}")
            return 0
        except RuntimeError as e:
            logger.warning(f"PolicyEngine API error for MA HEAP screen {self.screen.id}: {e}")
            return 0

        if payment is None:
            return 0

        return max(0, int(round(payment)))
