from ..base import UrgentNeedFunction
from integrations.services.income_limits import ami


class IlRenterAssistance(UrgentNeedFunction):
    ami_percent = "80%"
    dependencies = ["income_amount", "income_frequency", "household_size", "county"]
    
    def eligible(self):
        """
        Return True if the household is at or below 80% AMI using HUD 2025 income limits
        """
        print(f"IlRenterAssistance.eligible() - Screen ID: {self.screen.id}")
        print(f"County: {self.screen.county}")
        print(f"Household Size: {self.screen.household_size}")
        print(f"White Label ID: {self.screen.white_label_id}")
        print(f"White Label: {self.screen.white_label}")
        print(f"State Code: {self.screen.white_label.state_code if self.screen.white_label else 'NO WHITE LABEL'}")
        
        # Validate required fields
        if not self.screen.county or not self.screen.household_size:
            print("Missing county or household_size")
            return False
        
        if not self.urgent_need.year:
            print("Missing urgent_need.year")
            return False
        
        # Check if white_label and state_code exist
        if not self.screen.white_label:
            print("ERROR: screen.white_label is None")
            return False
            
        if not self.screen.white_label.state_code:
            print("ERROR: screen.white_label.state_code is None")
            return False
        
        print(f"Year: {self.urgent_need.year.period}")
        
        try:
            # Debug: Check what data structure looks like
            ami_data = ami.fetch()
            print(f"Available years: {list(ami_data.keys())}")
            
            if self.urgent_need.year.period in ami_data:
                print(f"Available states for {self.urgent_need.year.period}: {list(ami_data[self.urgent_need.year.period].keys())}")
                
                if self.screen.white_label.state_code in ami_data[self.urgent_need.year.period]:
                    print(f"Available counties in {self.screen.white_label.state_code}: {list(ami_data[self.urgent_need.year.period][self.screen.white_label.state_code].keys())}")
            
            income_limit = ami.get_screen_ami(
                self.screen, 
                self.ami_percent, 
                self.urgent_need.year.period, 
                limit_type="il"
            )
            print(f"Income Limit: {income_limit}")
        except (KeyError, TypeError, AttributeError) as e:
            print(f"AMI data error: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc()
            return False
            
        income = self.screen.calc_gross_income("yearly", ["all"])
        needs_housing_help = self.screen.needs_housing_help
        has_rent = self.screen.has_expense(["rent"])

        print(f"Income: {income}, needs_housing_help: {needs_housing_help}, has_rent: {has_rent}")
        
        return needs_housing_help and has_rent and income <= income_limit