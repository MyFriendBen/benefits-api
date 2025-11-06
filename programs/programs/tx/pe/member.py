from programs.programs.federal.pe.member import Wic, Ssi, CommoditySupplementalFoodProgram
import programs.programs.policyengine.calculators.dependencies as dependency
from screener.models import HouseholdMember


class TxWic(Wic):
    """
    Texas WIC calculator that uses PolicyEngine's calculated benefit amounts
    instead of state-specific category amounts.
    """

    pe_inputs = [
        *Wic.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]

    def member_value(self, member: HouseholdMember):
        """
        Returns the PolicyEngine-calculated WIC benefit amount for this member.
        Unlike the parent class, this doesn't use hardcoded category-based amounts.
        """
        return self.get_member_variable(member.id)


class TxSsi(Ssi):
    """
    Texas SSI calculator that uses PolicyEngine's calculated benefit amounts.
    Extends the federal SSI calculator with Texas state code dependency.
    """

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxCsfp(CommoditySupplementalFoodProgram):
    """
    Texas Commodity Supplemental Food Program (CSFP) calculator that uses PolicyEngine's calculations.
    Extends the federal CSFP calculator with Texas state code dependency.
    """

    pe_inputs = [
        *CommoditySupplementalFoodProgram.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
