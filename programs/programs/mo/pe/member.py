from programs.programs.federal.pe.member import (
    EarlyHeadStart,
)
import programs.programs.policyengine.calculators.dependencies as dependency


class MoEarlyHeadStart(EarlyHeadStart):
    """Missouri Early Head Start (birth-3 / pregnant) — federal ``EarlyHeadStart`` PE calculator + MO state code."""

    pe_inputs = [
        *EarlyHeadStart.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]
