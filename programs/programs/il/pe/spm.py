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

    tier_1_fpl = 1.30
    tier_2_fpl = 1.85

    tier_1_amount = 935
    tier_2_amount = 805

    def household_value(self):
        value = 0
        num_children = self.screen.num_children(3, 18)
        if self.get_variable() > 0 and num_children > 0:
            if self.get_dependency_value(dependency.spm.SchoolMealTier) != "PAID":
                countable_income = self.get_dependency_value(dependency.spm.SchoolMealCountableIncomeDependency)
                fpl_limit = self.program.year.get_limit(self.screen.household_size)

                if countable_income <= int(self.tier_1_fpl * fpl_limit):
                    value = self.tier_1_amount * num_children

                elif countable_income <= int(self.tier_2_fpl * fpl_limit):
                    value = self.tier_2_amount * num_children

        return value


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
    Illinois Low Income Home Energy Assistance Program (LIHEAP)

    Hard-coded annual benefit values based on household size.
    Eligibility: Income ≤ higher of (60% SMI or 200% FPL)
    Application period: October 1 to August 15

    Values based on IL 2025 benefit matrix for natural gas households.
    Source: https://liheapch.acf.gov/docs/2025/benefits-matricies/IL_BenefitMatrix_2025.pdf
    """

    pe_name = "il_liheap_income_eligible"  # Use income eligibility check instead of full program
    pe_inputs = [
        dependency.household.IlStateCodeDependency,
        dependency.spm.HasHeatingCoolingExpenseDependency,
        dependency.spm.HeatingCoolingExpenseDependency,
        *dependency.irs_gross_income,
    ]
    pe_outputs = [dependency.spm.IlLiheapIncomeEligible]

    # Hard-coded annual benefit amounts by household size
    benefit_amounts = {
        1: 315,
        2: 330,
        3: 340,
        4: 350,
        5: 365,
        6: 375,  # 6+ people
    }

    def household_value(self) -> int:
        """
        Calculate LIHEAP benefit based on hard-coded values by household size.

        Uses PolicyEngine for income eligibility check (60% SMI or 200% FPL),
        then returns hard-coded benefit amounts.

        Returns annual benefit amount (not monthly).
        """
        # Check PolicyEngine income eligibility (returns True/False)
        try:
            income_eligible = self.get_variable()  # il_liheap_income_eligible

            # If not income eligible, return 0
            if not income_eligible:
                return 0

            # Check if household has heating/cooling expenses
            has_heating_cooling = self.screen.has_expense(["heating", "cooling"])
            if not has_heating_cooling:
                return 0

            # Income eligible and has expenses - return hard-coded benefit
            household_size = self.screen.household_size
            size_key = min(household_size, 6)
            benefit = self.benefit_amounts.get(size_key, 0)
            return benefit

        except (KeyError, Exception):
            # If PE doesn't have the variable or throws error, return 0
            return 0
