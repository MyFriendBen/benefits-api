from screener.models import HouseholdMember
from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from integrations.services.sheets import GoogleSheetsCache
from programs.co_county_zips import counties_from_screen
import programs.programs.messages as messages


class CccapFplCache(GoogleSheetsCache):
    sheet_id = "1otQxo_hZu2pS1_1EBsPLVKP9HYFCdcYWZKNM24dbjvg"
    range_name = "current FPL %!A2:B"
    default = {}

    def update(self):
        data = super().update()

        county_fpls = {r[0] + " County": int(r[1]) for r in data}

        return county_fpls


class ChildCareAssistance(ProgramCalculator):
    preschool_value = 6000
    afterschool_value = 1700
    max_age_preschool = 4
    max_age_afterschool = 13
    max_age_afterschool_disabled = 19
    asset_limit = 1_000_000
    dependencies = [
        "age",
        "income_amount",
        "income_frequency",
        "zipcode",
        "household_size",
    ]
    fpl_limits = CccapFplCache()

    def household_eligible(self, e: Eligibility):
        cccap_county_limits = self.fpl_limits.fetch()

        # location
        counties = counties_from_screen(self.screen)
        in_county_limits = False
        county_name = counties[0]
        for county in counties:
            if county in cccap_county_limits:
                in_county_limits = True
                county_name = county
        e.condition(in_county_limits, messages.location())

        # income
        frequency = "yearly"
        gross_income = self.screen.calc_gross_income(frequency, ["all"], ["cashAssistance"])
        deductions = self.screen.calc_expenses(frequency, ["childSupport"])
        net_income = gross_income - deductions
        fpl_percent = cccap_county_limits.get(county_name, 0) / 100
        fpl = self.program.year.as_dict()
        income_limit = fpl[self.screen.household_size] * fpl_percent
        e.condition(net_income <= income_limit, messages.income(net_income, income_limit))

        # assets
        assets = self.screen.household_assets if self.screen.household_assets is not None else 0
        e.condition(
            assets < ChildCareAssistance.asset_limit,
            messages.assets(ChildCareAssistance.asset_limit),
        )

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # age
        child_eligible = False
        if member.age < ChildCareAssistance.max_age_afterschool:
            child_eligible = True
        elif (
            member.age >= ChildCareAssistance.max_age_afterschool
            and member.age <= ChildCareAssistance.max_age_afterschool_disabled
            and member.has_disability()
        ):
            child_eligible = True

        e.condition(child_eligible)

    def member_value(self, member: HouseholdMember):
        if member.age <= ChildCareAssistance.max_age_preschool:
            return ChildCareAssistance.preschool_value
        elif member.age < ChildCareAssistance.max_age_afterschool:
            return ChildCareAssistance.afterschool_value
        elif (
            member.age >= ChildCareAssistance.max_age_afterschool
            and member.age <= ChildCareAssistance.max_age_afterschool_disabled
            and member.has_disability()
        ):
            return ChildCareAssistance.afterschool_value

        return 0
