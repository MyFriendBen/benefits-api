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


class MAHeap(PolicyEngineSpmCalulator):
    """
    Massachusetts Home Energy Assistance Program (HEAP)

    Hard-coded annual benefit values based on household size.
    Eligibility: 60% state median income - current maximum income levels are here:
        Household Size      2026 Income Limit     2025 Income Limit
        1-person HH         $51,777               $49,196
        2                   $67,709               $64,333
        3                   $83,641               $79,470
        4                   $99,573               $94,608
        5                   $115,504              $109,745
        6                   $131,436              $124,882
        7                   $134,423
        8                   $137,410
    Application period: The online application will open on October 1, 2025,
        for the upcoming winter heating season (November 1, 2025, to April 30, 2026).

    Values based on MA 2025 benefit matrix for natural gas households.
    Source: https://liheapch.acf.gov/docs/2025/benefits-matricies/MA_BenefitMatrix_2025.pdf
    """

    pe_name = "ma_liheap_income_eligible"
    pe_inputs = [
        dependency.household.MaStateCodeDependency,
        dependency.spm.MALiheap,
    ]
    pe_outputs = [dependency.spm.MALiheapIncomeEligible]

    benefit_amounts = {
        1: 430,
        2: 445,
        3: 455,
        4: 465,
        5: 480,
        6: 490,  # 6+ people
    }

    def household_value(self) -> int:
        if self.screen.has_benefit("ma_heap"):
            return 0

        try:
            income_eligible = self.get_variable()  # ma_liheap_income_eligible
            if not income_eligible:
                return 0

            if not self.screen.has_expense(["heating", "cooling"]):
                return 0

            household_size = self.screen.household_size
            size_key = min(household_size, 6)
            benefit = self.benefit_amounts.get(size_key, 0)
            return benefit

        except KeyError as e:
            logger.warning(f"PolicyEngine missing expected key for MA HEAP screen {self.screen.id}: {e}")
            return 0
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning(f"Error calculating MA HEAP for screen {self.screen.id}: {type(e).__name__}: {e}")
            return 0
        except RuntimeError as e:
            logger.warning(f"PolicyEngine API error for MA HEAP screen {self.screen.id}: {e}")
            return 0
