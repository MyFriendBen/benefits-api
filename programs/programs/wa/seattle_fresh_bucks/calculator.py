from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages


class WaSeattleFreshBucks(ProgramCalculator):
    """
    Seattle Fresh Bucks — monthly $60 produce benefit for low-income Seattle residents.

    Eligibility:
    - Household income ≤ 80% AMI (King County/Seattle area)
    - Applicant must reside within Seattle city limits (ZIP code proxy)
    - Head of household must be 18 or older

    Data gaps: benefit is delivered via a lottery/waitlist; the calculator screens for
    eligibility only, not selection probability. Priority weighting (income tier,
    language preference) is not modeled.
    """

    amount = 60
    min_age = 18
    max_ami_percent = "80%"

    # Seattle city ZIP codes used as residency proxy per spec
    seattle_zip_codes = frozenset(
        [
            "98101",
            "98102",
            "98103",
            "98104",
            "98105",
            "98106",
            "98107",
            "98108",
            "98109",
            "98112",
            "98115",
            "98116",
            "98117",
            "98118",
            "98119",
            "98121",
            "98122",
            "98125",
            "98126",
            "98133",
            "98134",
            "98136",
            "98144",
            "98146",
            "98148",
            "98154",
            "98155",
            "98158",
            "98164",
            "98166",
            "98168",
            "98174",
            "98177",
            "98178",
            "98188",
            "98195",
            "98198",
            "98199",
        ]
    )

    dependencies = ("income_amount", "income_frequency", "household_size", "zipcode", "age")

    def household_eligible(self, e: Eligibility):
        # Location: must be within Seattle city limits (ZIP code proxy)
        in_seattle = self.screen.zipcode in self.seattle_zip_codes
        e.condition(in_seattle, messages.location())

        # Age: head of household must be at least 18
        head = self.screen.get_head()
        e.condition(head.age is not None and head.age >= self.min_age, messages.older_than(self.min_age))

        # Income: household gross income must be at or below 80% AMI (King County)
        try:
            income = self.screen.calc_gross_income("yearly", ["all"])
            income_limit = hud_client.get_screen_il_ami(self.screen, self.max_ami_percent, self.program.year.period)
            e.condition(income <= income_limit, messages.income(income, income_limit))
        except HudIncomeClientError:
            e.condition(False, messages.income_limit_unknown())
