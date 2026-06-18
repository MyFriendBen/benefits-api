from integrations.services.income_limits import ami
from programs.co_county_zips import counties_from_screen
from programs.programs.calc import MemberEligibility, ProgramCalculator, Eligibility
import programs.programs.messages as messages


class DenverPropertyTaxRelief(ProgramCalculator):
    amount = 252
    ami_percent_rental_single = 0.25
    ami_percent_rental_couple = 0.30
    ami_percent_mortgage = 0.60
    child_max_age = 17
    age_eligible = 65
    county = "Denver County"
    income_types = [
        "wages",
        "selfEmployment",
        "pension",
        "veteran",
        "unemployment",
        "investment",
        "cOSDisability",
        "rental",
        "alimony",
        "deferredComp",
        "workersComp",
        "boarder",
    ]
    mortgage_amount = 1_800
    rent_amount = 1_000
    dependencies = [
        "county",
        "income_amount",
        "income_frequency",
        "income_type",
        "expense_type",
        "household_size",
        "age",
        "relationship",
    ]

    def household_eligible(self, e: Eligibility) -> None:
        if self.program.year is None:
            return
        # county
        counties = counties_from_screen(self.screen)
        e.condition(DenverPropertyTaxRelief.county in counties, messages.location())

        # has rent or mortgage expense
        has_rent = self.screen.has_expense(["rent"])
        has_mortgage = self.screen.has_expense(["mortgage"])
        e.condition(has_rent or has_mortgage)

        # income
        multiple_adults = self.screen.num_adults(DenverPropertyTaxRelief.child_max_age + 1) >= 2
        ami_percent = -1
        if has_rent and multiple_adults:
            ami_percent = DenverPropertyTaxRelief.ami_percent_rental_couple
        elif has_rent:
            ami_percent = DenverPropertyTaxRelief.ami_percent_rental_single
        elif has_mortgage:
            ami_percent = DenverPropertyTaxRelief.ami_percent_mortgage

        limit = ami.get_screen_ami(self.screen, "100%", self.program.year.period) * ami_percent
        total_income = 0
        for member in self.screen.household_members.all():
            if member.is_head() or member.is_spouse():
                total_income += member.calc_gross_income("yearly", DenverPropertyTaxRelief.income_types)
        e.condition(total_income <= limit, messages.income(total_income, limit))

    def member_eligible(self, e: MemberEligibility) -> None:
        if e.member.age is None:
            return
        member = e.member

        # head or spouse
        e.condition(member.is_head() or member.is_spouse())

        has_child = self.screen.num_children(age_max=DenverPropertyTaxRelief.child_max_age) > 0

        # other condition
        other_condition = False
        if self.screen.has_expense(["mortgage"]) and has_child:
            other_condition = True

        if member.age >= DenverPropertyTaxRelief.age_eligible:
            other_condition = True

        if member.disabled or self.screen.has_benefit("ssi") or self.screen.has_benefit("ssdi"):
            other_condition = True

        e.condition(other_condition)

    def household_value(self):
        if self.screen.has_expense(["mortgage"]):
            return DenverPropertyTaxRelief.mortgage_amount
        elif self.screen.has_expense(["rent"]):
            return DenverPropertyTaxRelief.rent_amount

        return 0
