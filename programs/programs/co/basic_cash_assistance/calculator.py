import programs.programs.messages as messages
from programs.programs.calc import Eligibility, ProgramCalculator
from programs.co_county_zips import counties_from_screen


class BasicCashAssistance(ProgramCalculator):
    amount = 1_000
    county = "Denver County"
    dependencies = ["zipcode", "age"]

    def household_eligible(self, e: Eligibility) -> None:
        counties = counties_from_screen(self.screen)

        in_denver = BasicCashAssistance.county in counties
        e.condition(in_denver, messages.location())

        # Has a child
        num_children = self.screen.num_children()
        e.condition(num_children >= 1, messages.child())
