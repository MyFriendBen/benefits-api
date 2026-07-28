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
        has_wa_wap_eligible_benefit = (
            self.screen.has_benefit("wa_snap")
            or self.screen.has_benefit("wa_tanf")
            or self.screen.has_benefit("wa_ssi")
            # Section 8 is the HCV program (base_program "section_8", e.g. wa_hcv);
            # has_base_benefit matches every white-label variant, whereas the bare
            # has_benefit("section_8") is a dead check — that name_abbreviated exists nowhere.
            or self.screen.has_base_benefit("section_8")
        )

        categorically_eligible = has_wa_wap_eligible_benefit or any(
            member.has_insurance("wa_apple_health_medicaid") or member.has_insurance("wa_apple_health_for_kids")
            for member in self.screen.household_members.all()
        )

        if categorically_eligible:
            e.condition(True, messages.presumed_eligibility())
        else:
            gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
            income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
            e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
