from typing import ClassVar

from integrations.clients.hud_income_limits import HudIncomeClientError, hud_client
from integrations.clients.hud_income_limits.client import Section8AmiPercent
from programs.framework.base import Eligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages
from programs.util import DependencyError


class IlCbrap(ProgramCalculator):
    """
    Illinois Court-Based Rental Assistance Program (CBRAP) — IHDA.

    A one-time grant for Illinois renters already in eviction court over unpaid rent. The
    FY2026 round caps total assistance at $10,000 across past-due rent, up to two months of
    future rent, and up to $700 in court costs. It is a grant, not a loan. The program is
    currently paused; a warning message on the Program row says so.

    Eligibility:
    - Household gross income at or below 80% of the HUD Standard Section 8 income limit for
      its county and household size. The comparison is inclusive.
    - The household rents its home. The "in Illinois" half of that rule comes from the white
      label — every screen reaching this calculator is an Illinois screen.
    - No citizenship or immigration requirement. That rule lives entirely in the config's
      `legal_status_required`, which lists all six user-selectable statuses; this calculator
      never reads immigration status.

    Income-limit vintage: the vintage is a per-round parameter rather than the current year.
    IHDA used the FY2025 limits for the FY2026 round, which is why the config carries
    `year: "2025"` and the lookup passes `program.year.period`. A call made with the current
    year is a defect even when it returns a number.

    Value: a flat $7,692 — IHDA's FY2026 projection of $50,000,000 disbursed across 6,500
    approved households. The real award turns on rent arrears, court costs and remaining
    round funds, none of which the screener collects, so no per-household figure can be
    derived and the $10,000 cap would overstate nearly every award. This is a modelled
    estimate for display, not an entitlement. CBRAP Tenant Direct and the Cook County Right
    to Cure variant are reached through the same application and draw on the same pool, so
    they are not separate eligibility paths here.

    Replaces the `il_rent_asst` urgent need, which represented the same program with an
    extra `needs_housing_help` gate. That row must be deactivated in the release that
    activates this program, or Illinois renters see CBRAP twice under different rules.
    """

    program_code = "il_cbrap"

    ami_percent: ClassVar[Section8AmiPercent] = "80%"
    amount = 7_692
    dependencies: ClassVar[list[str]] = ["income_amount", "income_frequency", "household_size", "county"]

    def household_eligible(self, e: Eligibility):
        # Four CBRAP rules are unobservable in the screener and are assumed met. Each one
        # widens results rather than narrowing them, so the program description carries the
        # narrowing instead:
        # - assumed-met: the household is engaged in an active court eviction proceeding that
        #   includes non-payment of rent. No screener field identifies a court case.
        # - assumed-met: the rented unit is the household's primary residence. The screener
        #   records one rent expense and cannot distinguish a primary residence from any
        #   other rented unit.
        # - assumed-met: the household was not approved for CBRAP, tenant direct assistance
        #   included, in the previous 18 months. CurrentBenefit has no date column, so there
        #   is no receipt history to read.
        # - assumed-met: where the housing provider lives in the same multi-unit building, the
        #   household rents its own unit and is not a member of the provider's household. The
        #   screener records nothing about the landlord.

        # The importer only warns when the `year` row is missing, leaving program.year null.
        # Raise a named error rather than letting `.period` fail with an AttributeError.
        if not self.program.year:
            raise ValueError("program.year must be set to the HUD income limit vintage for IL CBRAP")

        # Tenure: CBRAP is for renters.
        e.condition(self.screen.has_expense(["rent"]))

        # Income: at or below 80% AMI for this county and household size, inclusive.
        #
        # Deliberately not gated on needs_housing_help. IlRenterAssistance gates on it, but
        # that is a narrowing proxy rather than the CBRAP rule — reusing it would deny
        # income-eligible renters who did not tick a housing-need box.
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))

        try:
            income_limit = hud_client.get_screen_il_ami(self.screen, self.ami_percent, self.program.year.period)
        except HudIncomeClientError as error:
            # A county HUD does not recognise, or an API failure, is missing data rather than
            # a policy answer. Drop the program from results the same way a missing screener
            # dependency does, instead of reporting the household ineligible for a rule that
            # was never evaluated.
            raise DependencyError() from error

        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
