from programs.framework.pe_base import PolicyEngineMembersCalculator
import programs.framework.pe_dependencies as dependency
from screener.models import HouseholdMember
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.wic.base import Wic
from programs.programs.cross_white_label.csfp.base import CommoditySupplementalFoodProgram


class AidToTheNeedyAndDisabled(PolicyEngineMembersCalculator):
    program_code = "andcs"
    pe_name = "co_state_supplement"
    pe_inputs = [
        dependency.member.SsiCountableResourcesDependency,
        # co_state_supplement tops up SSI, so it reads the `ssi` amount the receipt
        # contract supplies (reported where reported, simulated-and-suppressed otherwise).
        *dependency.receipt_contract,
        dependency.member.IsBlindDependency,
        dependency.member.IsDisabledDependency,
        dependency.member.SsiEarnedIncomeDependency,
        dependency.member.SsiUnearnedIncomeDependency,
        dependency.member.AgeDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.member.Andcs]


class OldAgePension(PolicyEngineMembersCalculator):
    program_code = "oap"
    pe_name = "co_oap"
    pe_inputs = [
        dependency.member.SsiCountableResourcesDependency,
        dependency.member.SsiEarnedIncomeDependency,
        dependency.member.SsiUnearnedIncomeDependency,
        dependency.member.AgeDependency,
        dependency.member.TaxUnitSpouseDependency,
        dependency.member.TaxUnitHeadDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.household.CoStateCodeDependency,
    ]
    pe_outputs = [dependency.member.Oap]


class Chp(PolicyEngineMembersCalculator):
    program_code = "chp"
    pe_name = "co_chp"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.PregnancyDependency,
        dependency.member.ExpectedChildrenPregnancyDependency,
        dependency.household.CoStateCodeDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.member.ChpEligible]

    amount = 200 * 12

    def member_value(self, member: HouseholdMember):
        chp_eligible = self.get_member_dependency_value(dependency.member.ChpEligible, member.id) > 0

        if chp_eligible and self.screen.has_insurance_types(("none",)):
            return self.amount

        return 0


class FamilyAffordabilityTaxCredit(PolicyEngineMembersCalculator):
    program_code = "fatc"
    pe_name = "co_family_affordability_credit"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.household.CoStateCodeDependency,
        dependency.member.TaxUnitSpouseDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.member.FamilyAffordabilityTaxCredit]
