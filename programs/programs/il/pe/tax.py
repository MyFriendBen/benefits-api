from programs.programs.federal.pe.tax import Eitc, Ctc
import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.policyengine.calculators.base import PolicyEngineTaxUnitCalulator


class Ileitc(PolicyEngineTaxUnitCalulator):
    pe_name = "il_eitc"
    pe_inputs = [
        *Eitc.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ileitc]

    def household_eligible(self, e):
        e.condition(not self.screen.has_benefit("il_eitc"))

        super().household_eligible(e)


class Ilctc(PolicyEngineTaxUnitCalulator):
    pe_name = "il_ctc"
    pe_inputs = [
        *Ctc.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]
    pe_outputs = [dependency.tax.Ilctc]

    def household_eligible(self, e):
        e.condition(not self.screen.has_benefit("il_ctc"))

        super().household_eligible(e)
