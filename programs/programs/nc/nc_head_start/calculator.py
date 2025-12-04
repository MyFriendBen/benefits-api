from integrations.services.sheets.sheets import GoogleSheetsCache
from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages
from programs.co_county_zips import counties_from_screen


class NcHeadStartMarketRatesCache(GoogleSheetsCache):
    expire_time = 60 * 60 * 24
    default = {}
    sheet_id = "1y7p8qkiOrMAM42rtSwT_ZXeA5tzew4edNkrTXACxf4M"
    range_name = "'Current report'!A2:F101"
    
    def update(self):
        data = super().update()        
        rates = {}
        for row in data:
            if len(row) < 6:
                continue
            county_name = row[0].strip()
            # Convert market rate strings to integers, removing commas
            rates[county_name] = {
                "infant": int(row[1].replace(',', '')) if row[1] else 0,  # 0-1 years
                "toddler": int(row[2].replace(',', '')) if row[2] else 0,  # 2 years
                "preschool": int(row[3].replace(',', '')) if row[3] else 0,  # 3-5 years
                "school_age": int(row[4].replace(',', '')) if row[4] else 0,  # 6-12 years
                "teen_disabled": int(row[5].replace(',', '')) if row[5] else 0,  # 12-17 with disabilities
            }
        
        return rates


class NCHeadStart(ProgramCalculator):
    amount = 0
    member_amount = 0
    min_age = 0
    max_age = 5
    max_age_disabled = 17
    fpl_percent = 1.3  # 130% FPL
    market_rates = NcHeadStartMarketRatesCache()
    housing_cost_percent = 0.30  # 30% threshold for rent expense
    # Only these income types are counted for NC Head Start
    countable_income_types = ["wages", "selfEmployment", "unemployment", "pension", "veteran"]
    # Automatic eligibility for households receiving these benefits
    presumptive_eligibility = ["snap", "tanf", "ssi"]
    dependencies = ["age", "household_size", "income_frequency", "income_type", "income_amount", "zipcode"]

    def household_eligible(self, e: Eligibility):
        # location - check if county has market rates (means it's eligible)
        counties = counties_from_screen(self.screen)        
        market_rates_data = NCHeadStart.market_rates.fetch()
        
        in_eligible_county = False
        for county in counties:
            if county in market_rates_data:
                in_eligible_county = True
                break
        
        e.condition(in_eligible_county, messages.location())

        # Automatic eligibility for households receiving SNAP, TANF, or SSI
        has_presumptive_benefit = self.screen.has_benefit_from_list(NCHeadStart.presumptive_eligibility)
                
        if has_presumptive_benefit:
            # Skip income check - automatically eligible
            e.condition(True, messages.presumed_eligibility())
        else:
            # income - 130% FPL with housing cost adjustment
            fpl = self.program.year.as_dict()
            household_size = self.screen.household_size
            income_limit = int(fpl[household_size] * NCHeadStart.fpl_percent)
            
            # Calculate gross countable income (only specific income types count)
            gross_income = int(self.screen.calc_gross_income("yearly", NCHeadStart.countable_income_types))
            # print(f"NC Head Start gross countable income: {gross_income}, Income limit (130% FPL): {income_limit}")
            
            # If income is over 130% FPL, check for housing cost adjustment
            countable_income = gross_income
            if gross_income > income_limit:
                # Check if household has rent expense
                has_rent = self.screen.has_expense(["rent"])
                if has_rent:
                    # Calculate housing cost adjustment
                    rent_expense = int(self.screen.calc_expenses("yearly", ["rent"]))
                    housing_cost_threshold = gross_income * NCHeadStart.housing_cost_percent
                    
                            
                    # If rent exceeds 30% of gross income, deduct the excess
                    if rent_expense > housing_cost_threshold:
                        housing_cost_adjustment = rent_expense - housing_cost_threshold
                        countable_income = max(0, gross_income - housing_cost_adjustment)        
            
            # Check if adjusted income is below limit
            e.condition(countable_income <= income_limit, messages.income(countable_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age - 0-5 years, or 6-17 with disability, or pregnant
        is_eligible_age = (
            (member.age >= NCHeadStart.min_age and member.age <= NCHeadStart.max_age) or
            (member.age > NCHeadStart.max_age and member.age <= NCHeadStart.max_age_disabled and member.has_disability())
        )
        is_pregnant = member.pregnant        
        
        e.condition(is_eligible_age or is_pregnant)
    
    def household_value(self):
        """
        Calculate estimated annual savings based on county market rates and children's ages.
        Formula: Sum of (monthly market rates * 12) for all eligible children
        """
        counties = counties_from_screen(self.screen)
        market_rates_data = NCHeadStart.market_rates.fetch()
        
        county_rates = None
        for county in counties:
            if county in market_rates_data:
                county_rates = market_rates_data[county]
                break
        
        if not county_rates:
            return 0
        
        total_annual_rate = 0
        
        # Calculate total market rate for all eligible children
        for member in self.screen.household_members.all():
            # Check if member meets eligibility criteria
            is_eligible_age = (
                (member.age >= NCHeadStart.min_age and member.age <= NCHeadStart.max_age) or
                (member.age > NCHeadStart.max_age and member.age <= NCHeadStart.max_age_disabled and member.has_disability())
            )
            is_pregnant = member.pregnant
            
            # Skip if not eligible
            if not (is_eligible_age or is_pregnant):
                continue
            
            # Determine monthly rate based on age
            monthly_rate = 0
            
            # Handle pregnant person - use infant rate
            if is_pregnant:
                monthly_rate = county_rates["infant"]
            elif member.age <= 1:
                monthly_rate = county_rates["infant"]
            elif member.age == 2:
                monthly_rate = county_rates["toddler"]
            elif 3 <= member.age <= 5:
                monthly_rate = county_rates["preschool"]
            elif 6 <= member.age <= 12:
                monthly_rate = county_rates["school_age"]
            elif 12 < member.age <= 17 and member.has_disability():
                monthly_rate = county_rates["teen_disabled"]
                        
            # Annual rate (monthly * 12)
            total_annual_rate += monthly_rate * 12
        
        return total_annual_rate
    
    def member_value(self, member):
        """
        Member value is calculated at the household level in household_value().
        Return 0 here to avoid double-counting.
        """
        return 0










