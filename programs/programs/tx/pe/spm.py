import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap, Lifeline, SchoolLunch


class TxSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxLifeline(Lifeline):
    pe_inputs = [
        *Lifeline.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]


class TxNslp(SchoolLunch):
    """
    Texas National School Lunch Program (NSLP) calculator.

    Uses PolicyEngine-calculated benefit amounts for TX-specific NSLP eligibility
    and benefit values. Inherits from federal SchoolLunch calculator and adds
    TX state code dependency.
    """

    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.TxStateCodeDependency,
    ]
