from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
from programs.programs import messages


class TxHtw(ProgramCalculator):
    """
    Healthy Texas Women (HTW)

    Free health services program for Texas women ages 15-44 with household income
    at or below 204.2% FPL. Covers family planning, birth control, annual checkups,
    and health screenings at no cost. No fixed dollar benefit — services are provided
    without cost sharing.

    Data gaps: screener has no sex/gender field (gender criterion assumed met for all
    members); citizenship/immigration handled via legal_status_required config.
    """

    fpl_percent = 2.042
    min_age = 15
    max_age = 44
    dependencies = [
        "age",
        "household_size",
        "income_amount",
        "income_frequency",
        "pregnant",
        "health_insurance",
    ]

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Age 15-44
        e.condition(member.age is not None and self.min_age <= member.age <= self.max_age)

        # Not pregnant (pregnant women referred to Medicaid for Pregnant Women)
        e.condition(not member.pregnant)

        # Not enrolled in Medicaid or CHIP, and no other comprehensive health insurance (Medicare, employer, private, or VA)
        e.condition(
            not member.insurance.has_insurance_types(["medicaid", "chp", "medicare", "employer", "private", "va"])
        )

    def household_eligible(self, e: Eligibility):
        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
