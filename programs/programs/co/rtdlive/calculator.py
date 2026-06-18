from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
from programs.co_county_zips import counties_from_screen
import programs.programs.messages as messages
from screener.models import HouseholdMember


class RtdLive(ProgramCalculator):
    eligible_counties = [
        "Adams County",
        "Arapahoe County",
        "Boulder County",
        "Broomfield County",
        "Denver County",
        "Douglas County",
        "Jefferson County",
    ]
    min_age = 20
    max_age = 64
    percent_of_fpl = 2.5
    member_amount = 732
    dependencies = ["age", "income_amount", "income_frequency", "zipcode", "household_size"]

    def household_eligible(self, e: Eligibility) -> None:
        # location
        county_eligible = False
        counties = counties_from_screen(self.screen)

        for county in counties:
            if county in RtdLive.eligible_counties:
                county_eligible = True

        e.condition(county_eligible, messages.location())

    def member_eligible(self, e: MemberEligibility) -> None:
        if self.program.year is None:
            return
        member = e.member

        # age
        if member.age is None:
            return
        e.condition(RtdLive.min_age <= member.age <= RtdLive.max_age)

        # income
        if member.is_in_tax_unit():
            tax_unit = [m for m in self.screen.household_members.all() if m.is_in_tax_unit()]
        else:
            tax_unit = [m for m in self.screen.household_members.all() if not m.is_in_tax_unit()]

        e.condition(self._unit_income_eligible(tax_unit))

    def _unit_income_eligible(self, members: list[HouseholdMember]) -> bool:
        gross_income = 0
        for member in members:
            gross_income += member.calc_gross_income("yearly", ["all"])

        fpl = self.program.year.as_dict()
        income_limit = RtdLive.percent_of_fpl * fpl[len(members)]

        return gross_income <= income_limit
