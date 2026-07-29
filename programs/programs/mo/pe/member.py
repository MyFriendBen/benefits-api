from programs.programs.federal.pe.member import (
    HeadStart,
    EarlyHeadStart,
)
import programs.programs.policyengine.calculators.dependencies as dependency


class MoHeadStart(HeadStart):
    """Missouri Head Start (ages 3-5) — federal ``HeadStart`` PE calculator + MO state code."""

    pe_inputs = [
        *HeadStart.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]


class MoEarlyHeadStart(EarlyHeadStart):
    """Missouri Early Head Start (birth-3 / pregnant) — federal ``EarlyHeadStart`` PE calculator + MO state code."""

    pe_inputs = [
        *EarlyHeadStart.pe_inputs,
        dependency.household.MoStateCodeDependency,
    ]
