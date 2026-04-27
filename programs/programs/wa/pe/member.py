from programs.programs.federal.pe.member import Ssi
import programs.programs.policyengine.calculators.dependencies as dependency


class WaSsi(Ssi):
    """
    Washington SSI calculator that uses PolicyEngine's calculated benefit amounts.
    Extends the federal SSI calculator with Washington state code dependency so
    PolicyEngine evaluates SSI eligibility against WA-specific rules
    (e.g. WA's optional state supplement).
    """

    pe_inputs = [
        *Ssi.pe_inputs,
        dependency.household.WaStateCodeDependency,
    ]
