"""MaHeap."""

from programs.framework.pe_base import PolicyEngineSpmCalulator
import programs.framework.pe_dependencies as dependency


class MaHeap(PolicyEngineSpmCalulator):
    program_code = "ma_heap"
    pe_name = "ma_liheap"

    pe_inputs = [
        dependency.household.MaStateCodeDependency,
        *dependency.irs_gross_income,
        dependency.spm.MaLiheapReceivesHousingAssistance,
        dependency.spm.MaLiheapHeatExpenseIncludedInRent,
        dependency.spm.HasHeatingCoolingExpenseDependency,
        # Final payment is min(payment_amount, heating + gas + electricity expense).
        # PE's state LIHEAP reads heating from heating_expense_person (person-level)
        # and auto-aggregates to the spm_unit total. Without this PE sees $0 of
        # heating expense and caps the benefit at $0.
        dependency.member.HeatingExpensePersonDependency,
        dependency.spm.ElectricityExpenseDependency,
    ]

    pe_outputs = [
        dependency.spm.MaLiheap,
    ]
