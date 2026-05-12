from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages


class WaHcv(ProgramCalculator):
    """
    WA Housing Choice Voucher (Section 8) — variable rental subsidy for low-income households.

    Eligibility: VLI (50% AMI) income test, assets ≤ $100k, not currently on Section 8.
    Benefit: HAP = Payment Standard (100% FMR) minus Total Tenant Payment.
    Data gaps: citizenship, criminal history, real property ownership, student dual-income test.
    """

    amount = 0
    asset_limit = 100_000
    dependent_deduction_annual = 480
    elderly_disabled_deduction_annual = 525
    min_rent_monthly = 50

    BEDROOM_MAP = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4}

    dependencies = (
        "income_amount",
        "income_frequency",
        "household_size",
        "county",
        "zipcode",
        "household_assets",
        "age",
        "relationship",
    )

    def _effective_household_size(self) -> int:
        """Pregnant single person → 2-person family per 24 CFR § 982.402(b)(5)."""
        if self.screen.household_size == 1:
            head = self.screen.get_head()
            if head and head.pregnant:
                return 2
        return self.screen.household_size

    def _estimate_bedrooms(self) -> int:
        hh_size = self._effective_household_size()
        return self.BEDROOM_MAP.get(hh_size, 4)

    def _count_dependents(self) -> int:
        """Under 18, student, or disabled — excluding head and spouse (24 CFR § 5.611)."""
        count = 0
        for member in self.screen.household_members.all():
            if member.relationship in ("headOfHousehold", "spouse"):
                continue
            is_dependent = (member.age is not None and member.age < 18) or member.student or member.has_disability()
            if is_dependent:
                count += 1
        return count

    def _is_elderly_or_disabled_family(self) -> bool:
        """True if head, spouse, or sole member is 62+ or has a disability."""
        for member in self.screen.household_members.all():
            if member.relationship in ("headOfHousehold", "spouse"):
                if (member.age is not None and member.age >= 62) or member.has_disability():
                    return True
        return False

    def _get_year_period(self) -> str:
        if self.program.year is None:
            raise HudIncomeClientError("Program year not configured")
        return self.program.year.period

    def household_eligible(self, e: Eligibility):
        has_section_8 = self.screen.has_benefit("section_8")
        e.condition(not has_section_8, messages.must_not_have_benefit("Section 8"))

        assets = self.screen.household_assets if self.screen.household_assets is not None else 0
        e.condition(assets <= self.asset_limit, messages.assets(self.asset_limit))

        try:
            year_period = self._get_year_period()
            gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
            effective_hh = self._effective_household_size()
            original_hh = self.screen.household_size
            try:
                self.screen.household_size = effective_hh
                income_limit = hud_client.get_screen_il_ami(self.screen, "50%", year_period)
            finally:
                self.screen.household_size = original_hh
            e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
        except HudIncomeClientError:
            e.condition(False, messages.income_limit_unknown())

    def household_value(self) -> int:
        try:
            gross_income = self.screen.calc_gross_income("yearly", ["all"])
            monthly_gross = gross_income / 12

            dependent_deduction = self._count_dependents() * self.dependent_deduction_annual
            elderly_deduction = self.elderly_disabled_deduction_annual if self._is_elderly_or_disabled_family() else 0
            annual_adjusted = gross_income - dependent_deduction - elderly_deduction
            monthly_adjusted = annual_adjusted / 12

            ttp = max(0.30 * monthly_adjusted, 0.10 * monthly_gross, self.min_rent_monthly)

            bedrooms = self._estimate_bedrooms()
            fmr = hud_client.get_screen_fmr(self.screen, bedrooms, self._get_year_period())

            hap = max(0, fmr - ttp)
            return int(hap * 12)
        except HudIncomeClientError:
            return 0
