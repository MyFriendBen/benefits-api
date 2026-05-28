import programs.programs.messages as messages
from programs.programs.calc import Eligibility, ProgramCalculator
from typing import ClassVar


class WaWap(ProgramCalculator):
    """
    Weatherization Assistance Program — Washington State.

    Provides free home energy upgrades (insulation, heating repair/replacement,
    air sealing) to reduce energy costs. Estimated one-time value: up to $7,669 per home.

    Income at or below 200% FPL qualifies. Federal categorical eligibility via
    TANF, SSI, or SNAP bypasses the income test. WA state-level expansion also
    grants categorical eligibility to households receiving Section 8 or Medicaid
    (Apple Health) — note this is a state-level extension accepted by WA sub-grantees.

    Data gaps (not evaluated): prior weatherization history (15-year re-weatherization
    rule), dwelling type (must be residential), local agency service area, multifamily
    building occupancy test, post-eligibility energy audit, Seattle HomeWise 80% AMI
    variation. State residency is enforced via the `wa` white label routing.
    """

    fpl_percent = 2.0
    amount = 7_669  # one-time lump-sum per WA Commerce estimate

    dependencies: ClassVar[list[str]] = [
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def household_eligible(self, e: Eligibility):
        categorically_eligible = (
            self.screen.has_benefit("snap")
            or self.screen.has_benefit("tanf")
            or self.screen.has_benefit("ssi")
            or self.screen.has_benefit("section_8")
            or self.screen.has_benefit("medicaid")
        )

        if categorically_eligible:
            e.condition(True, messages.presumed_eligibility())
        else:
            gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
            income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
            e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
