from ..base import UrgentNeedFunction


class SNAPApplicationAssistance(UrgentNeedFunction):
    dependencies = ["county", "income_amount", "income_frequency", "household_size"]
    eligible_city = "Cambridge"
    fpl_percent = 2

    def eligible(self) -> bool:
        """
        CEOC - SNAP Application Assistance
        Free help applying for SNAP food benefits.

        Eligibility:
        -Up to 200% FPL (gross)
        -Must meet MA SNAP rules
        -Cambridge resident
        """

        # Condition 1: Cambridge residents
        is_cambridge = self.screen.county == self.eligible_city

        # Condition 2: Not receiving SNAP
        has_snap = self.screen.has_benefit("ma_snap")

        # Condition 3: SNAP Eligible
        is_snap_eligible = False

        for program in self.data:
            print(program["name_abbreviated"], program["eligible"])
            if program["name_abbreviated"] != "ma_snap":
                continue

            if program["eligible"]:
                is_snap_eligible = True
                break

        # Condition 4: Income
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.fpl_percent * self.urgent_need.year.get_limit(self.screen.household_size))
        is_income_eligible = gross_income <= income_limit

        return is_cambridge and is_snap_eligible and is_income_eligible and not has_snap
