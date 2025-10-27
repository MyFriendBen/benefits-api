from ..base import UrgentNeedFunction
from integrations.services.income_limits import ami


class IlRenterAssistance(UrgentNeedFunction):
    ami_percent = "80%"
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]
    

    def eligible(self):
        """
        Return True if the household is at or below 80% the income limit for their household size
        """
        print(f"IlRenterAssistance.eligible() called for screen {vars(self.screen)}")
        # income_limit = self.urgent_need.year.as_dict()[self.screen.household_size] * self.ami_percent
        # income_limit = ami.get_screen_ami(
        #     self.screen, self.ami_percent, self.urgent_need.year.period, limit_type="il"
        # )
        # income_limit = ami.get_screen_ami(self.screen, "80%", self.urgent_need.year.period) * self.ami_percent

        print("self.screen.county:",self.screen.county)
        print("self.screen.household_size:",self.screen.household_size)
         # Validate required fields
        if not self.screen.county or not self.screen.household_size:
            return False
        
        print("self.urgent_need.year.period:",self.urgent_need.year.period)
        # Check if year is set - this is required for AMI lookup
        if not self.urgent_need.year.period:
            return False
        
        try:
            # Get 80% AMI from HUD data for Illinois
            print("income_limit:")
            income_limit = ami.get_screen_ami(
                self.screen, 
                self.ami_percent, 
                self.urgent_need.year.period, 
                limit_type="il"
            )
            print("income_limit:",income_limit)
        except (KeyError, TypeError, AttributeError):
            # County data may not be available in HUD database
            return False
        

        income = self.screen.calc_gross_income("yearly", ["all"])
        
        # # Condition 1: Household needs housing/utilities help
        needs_housing_help = self.screen.needs_housing_help

        # # Condition 2: Household has rent expense
        has_rent = self.screen.has_expense(["rent"])

        # # Remove this debug code before creating PR
        print(
            f"Income Limit: {income_limit}, Income: {income}, needs_housing_help: {needs_housing_help}, has_rent: {has_rent}"
        )

        return needs_housing_help and has_rent and income <= income_limit
        # return needs_housing_help and has_rent
