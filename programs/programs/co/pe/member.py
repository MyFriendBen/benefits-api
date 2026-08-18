from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.programs.federal.pe.member import CommoditySupplementalFoodProgram, Medicaid
from programs.programs.federal.pe.member import Wic
import programs.framework.pe_dependencies as dependency
from screener.models import HouseholdMember


class CoMedicaid(Medicaid):
    name_abbreviated = "co_medicaid"
    medicaid_categories = {
        "NONE": 0,
        "ADULT": 310,
        "INFANT": 200,
        "YOUNG_CHILD": 200,
        "OLDER_CHILD": 200,
        "PREGNANT": 310,
        "YOUNG_ADULT": 310,
        "PARENT": 310,
        "SSI_RECIPIENT": 310,
        "AGED": 170,
        "DISABLED": 310,
    }
    pe_inputs = [
        *Medicaid.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]


class AidToTheNeedyAndDisabled(PolicyEngineMembersCalculator):
    name_abbreviated = "andcs"
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
    name_abbreviated = "oap"
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
    name_abbreviated = "chp"
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
    name_abbreviated = "fatc"
    pe_name = "co_family_affordability_credit"
    pe_inputs = [
        dependency.member.AgeDependency,
        dependency.member.TaxUnitDependentDependency,
        dependency.household.CoStateCodeDependency,
        dependency.member.TaxUnitSpouseDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.member.FamilyAffordabilityTaxCredit]


class CoWic(Wic):
    name_abbreviated = "co_wic"
    wic_categories = {
        "NONE": 0,
        "INFANT": 130,
        "CHILD": 79,
        "PREGNANT": 104,
        "POSTPARTUM": 88,
        "BREASTFEEDING": 121,
    }
    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.CoStateCodeDependency,
    ]


class EveryDayEats(CommoditySupplementalFoodProgram):
    name_abbreviated = "ede"
    amount = 600

    def member_value(self, member: HouseholdMember):
        ede_eligible = self.get_member_variable(member.id) > 0

        if ede_eligible:
            return self.amount

        return 0
