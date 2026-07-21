from programs.programs.policyengine.calculators.base import PolicyEngineSpmCalulator
import programs.programs.policyengine.calculators.dependencies as dependency
from programs.programs.federal.pe.spm import Snap, SchoolLunch, Tanf


class IlSnap(Snap):
    pe_inputs = [
        *Snap.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]


class IlNslp(SchoolLunch):
    pe_inputs = [
        *SchoolLunch.pe_inputs,
        dependency.household.IlStateCodeDependency,
    ]


class IlTanf(Tanf):
    pe_name = "il_tanf"
    pe_inputs = [
        *Tanf.pe_inputs,
        dependency.household.IlStateCodeDependency,
        dependency.spm.IlTanfCountableEarnedIncomeDependency,
        dependency.spm.IlTanfCountableGrossUnearnedIncomeDependency,
    ]

    pe_outputs = [dependency.spm.IlTanf]


class IlLiheap(PolicyEngineSpmCalulator):
    """
    Illinois Low Income Home Energy Assistance Program (LIHEAP).

    Delegates the full eligibility and benefit calculation to PolicyEngine's
    ``il_liheap`` variable (2026 benefit matrix), rather than hard-coding amounts.

    PolicyEngine computes:
      - Income eligibility: gross income <= higher of 60% SMI or 200% FPL.
      - Benefit: an annual matrix amount keyed on fuel type, income bracket, and
        household size, capped at the household's reported heating expense
        (``min(matrix_amount, heating)``). PE models every IL household as
        "All Electric" (or "Cash" when heat is included in rent).

    Required PE input is ``heating_expense_person``: our screener captures heating
    at the household level, so ``HeatingExpensePersonDependency`` assigns the full
    amount to the head, which PE aggregates to the SPM unit for the cap. Because
    the benefit is capped at this expense, a household reporting no heating/cooling
    expense receives $0.

    Households that already receive IL LIHEAP are flagged and handled by the
    results layer (via ``already_has``), not in this calculator.
    """

    pe_name = "il_liheap"
    pe_inputs = [
        dependency.household.IlStateCodeDependency,
        *dependency.irs_gross_income,
        dependency.spm.HasHeatingCoolingExpenseDependency,
        dependency.member.HeatingExpensePersonDependency,
        dependency.spm.ElectricityExpenseDependency,
    ]
    pe_outputs = [dependency.spm.IlLiheap]
