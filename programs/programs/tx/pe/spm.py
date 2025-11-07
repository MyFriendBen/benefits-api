import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap, Lifeline, SchoolLunch, Tanf


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


class TxTanf(Tanf):
    """
    Texas Temporary Assistance for Needy Families (TANF) calculator.

    Uses PolicyEngine-calculated benefit amounts for TX-specific TANF eligibility
    and benefit values. Inherits from federal TANF calculator and adds TX state
    code dependency and TX-specific income dependencies.
    """

    pe_name = "tx_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.TxStateCodeDependency,
        dependency.spm.TxTanfCountableEarnedIncomeDependency,
        dependency.spm.TxTanfCountableUnearnedIncomeDependency,
    ]

    pe_outputs = [dependency.spm.TxTanf]
