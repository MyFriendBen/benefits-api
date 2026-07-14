import logging
from types import MappingProxyType

from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from programs.programs.calc import Eligibility, ProgramCalculator
import programs.programs.messages as messages

logger = logging.getLogger(__name__)


class TxHcv(ProgramCalculator):
    """
    TX Housing Choice Voucher (Section 8) — TDHCA-administered rental subsidy for
    low-income households. MFB custom calculator (no PolicyEngine dependency),
    mirroring the shipped WA HCV precedent.

    Eligibility (hard gates implemented in MFB logic):
      - Household income at or below 50% AMI ("Very Low Income", 24 CFR 982.201);
        looked up per county/size from HUD's Section 8 Income Limits.
      - Not already receiving Section 8 / HCV (24 CFR 982.551(n)).
      - Head of household at least 18 (legal capacity to lease, 24 CFR 5.504(b)).
      - Net household assets at or below the $100k HOTMA limit when reported
        (24 CFR 5.618).

    Benefit value: monthly HAP = min(payment standard, gross rent) − TTP, floored
    at $0, annualized. Payment standard = HUD FMR (metro/county) or ZIP-level SAFMR
    for the four TX mandatory-SAFMR metros (Dallas, Fort Worth-Arlington, San
    Antonio-New Braunfels, Beaumont-Port Arthur), via
    ``hud_client.get_screen_payment_standard``. TTP = highest of 30% of monthly
    adjusted income, 10% of monthly gross income, and TDHCA's $25/month minimum
    rent, rounded to the nearest dollar (24 CFR 5.628).

    Income exclusions (24 CFR 5.609(b)) applied to BOTH the income gate and the
    value calc: a member under 18's earned income is excluded (unearned still
    counts); a foster child's income is excluded entirely.

    Adjusted-income deductions (24 CFR 5.611): $480/year per dependent (foster
    children never count), plus $525/year once if the family is elderly (head/
    spouse 62+) or disabled.

    Documented data gaps handled inclusively (assumed to pass): criminal
    background, PHA discretionary history, drug-related eviction, and student
    restrictions. Deferred simplifications (match WA HCV): utility allowance,
    medical/childcare deductions, mixed-status proration, live-in aides.
    """

    amount = 0
    asset_limit = 100_000
    min_head_age = 18
    ami_percent = "50%"
    dependent_deduction_annual = 480
    elderly_disabled_deduction_annual = 525
    min_rent_monthly = 25

    # Household size → voucher bedroom size (24 CFR 982.402; TDHCA Ch. 5 Part II).
    # A single-person household defaults to 0BR (TDHCA's conservative choice).
    # Immutable (MappingProxyType) to prevent accidental shared-state mutation.
    BEDROOM_MAP = MappingProxyType({1: 0, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4})

    _elderly_family_relationships = ("headOfHousehold", "spouse", "domesticPartner")

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

    def _year_period(self) -> str:
        if self.program.year is None:
            raise HudIncomeClientError("Program year not configured")
        return self.program.year.period

    def _countable_gross_income(self) -> float:
        """
        Annual gross income with 24 CFR 5.609(b) exclusions applied: a member
        under 18 has earned income excluded (unearned still counts); a foster
        child's income is excluded entirely.
        """
        total = 0.0
        for member in self.screen.household_members.all():
            if member.relationship == "fosterChild":
                continue
            if member.age is not None and member.age < 18:
                total += member.calc_gross_income("yearly", ["unearned"])
            else:
                total += member.calc_gross_income("yearly", ["all"])
        return total

    def _estimate_bedrooms(self) -> int:
        return self.BEDROOM_MAP.get(self.screen.household_size, 4)

    def _count_dependents(self) -> int:
        """
        Dependents per 24 CFR 5.611: a member other than head/spouse/co-head who
        is under 18, or 18+ and disabled or a full-time student. Foster children
        never count.
        """
        count = 0
        for member in self.screen.household_members.all():
            if member.relationship in self._elderly_family_relationships:
                continue
            if member.relationship == "fosterChild":
                continue
            if member.age is None:
                continue
            under_18 = member.age < 18
            adult_dependent = member.age >= 18 and (member.has_disability() or member.student_full_time)
            if under_18 or adult_dependent:
                count += 1
        return count

    def _is_elderly_or_disabled_family(self) -> bool:
        """$525 deduction if head/spouse/co-head is 62+ or disabled (24 CFR 5.611(a)(2))."""
        for member in self.screen.household_members.all():
            if member.relationship in self._elderly_family_relationships:
                if (member.age is not None and member.age >= 62) or member.has_disability():
                    return True
        return False

    def _head_age_ok(self) -> bool:
        """Head of household must be at least 18 (24 CFR 5.504(b)). Unknown age
        does not block — the gate only rejects a head known to be under 18."""
        head = self.screen.get_head()
        if head is None or head.age is None:
            return True
        return head.age >= self.min_head_age

    def household_eligible(self, e: Eligibility):
        # Criterion 2: not already receiving Section 8 / HCV assistance.
        # "Section 8" is the HCV program itself (base_program "section_8"): tx_hcv,
        # wa_hcv, co_section_8, etc. Use has_base_benefit so it matches every
        # white-label variant
        e.condition(not self.screen.has_base_benefit("section_8"), messages.must_not_have_benefit("Section 8"))

        # Criterion 9: HOTMA net-asset limit — only a gate when reported over $100k.
        assets = self.screen.household_assets if self.screen.household_assets is not None else 0
        e.condition(assets <= self.asset_limit, messages.assets(self.asset_limit))

        # Criterion 3: head of household must be at least 18.
        e.condition(self._head_age_ok(), messages.older_than(self.min_head_age))

        # Criterion 1: income at or below 50% AMI (Very Low Income).
        # Never let a HUD lookup failure raise out of the calculator and break the
        # whole eligibility run — the safest guess for an income gate we can't
        # evaluate is "not eligible".
        try:
            gross_income = int(self._countable_gross_income())
            income_limit = hud_client.get_screen_il_ami(self.screen, self.ami_percent, self._year_period())
            e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))
        except HudIncomeClientError:
            # Expected when HUD data is unavailable (API down, county/ZIP not found,
            # year unconfigured) — mark not eligible without noise.
            e.condition(False, messages.income_limit_unknown())
        except Exception:
            # Unexpected failure — still degrade to not eligible rather than raise,
            # and log so it's observable.
            logger.exception(
                "TxHcv.household_eligible income check failed unexpectedly (white_label=%s, household_size=%s)",
                getattr(self.screen.white_label, "code", None),
                self.screen.household_size,
            )
            e.condition(False, messages.income_limit_unknown())

    def household_value(self) -> int:
        try:
            gross_income = self._countable_gross_income()
            monthly_gross = gross_income / 12

            dependent_deduction = self._count_dependents() * self.dependent_deduction_annual
            elderly_deduction = self.elderly_disabled_deduction_annual if self._is_elderly_or_disabled_family() else 0
            annual_adjusted = gross_income - dependent_deduction - elderly_deduction
            monthly_adjusted = annual_adjusted / 12

            ttp = max(0.30 * monthly_adjusted, 0.10 * monthly_gross, self.min_rent_monthly)
            ttp = int(ttp + 0.5)  # round to the nearest dollar (24 CFR 5.628)

            bedrooms = self._estimate_bedrooms()
            payment_standard = hud_client.get_screen_payment_standard(self.screen, bedrooms, self._year_period())

            # Gross rent = the household's reported rent when available (lower of it
            # and the payment standard), else the payment standard alone.
            reported_rent = self.screen.calc_expenses("monthly", ["rent", "mortgage"])
            gross_rent = min(payment_standard, reported_rent) if reported_rent > 0 else payment_standard

            hap = max(0, gross_rent - ttp)
            return int(hap * 12)
        except HudIncomeClientError:
            # Expected when HUD data is unavailable (API down, county/ZIP not found,
            # year unconfigured) — degrade to $0 without noise.
            return 0
        except Exception:
            # Unexpected bug in the value calculation — still degrade to $0 so one
            # program can't 500 the whole eligibility response, but log it so the
            # failure is observable rather than silently swallowed.
            logger.exception(
                "TxHcv.household_value failed unexpectedly (white_label=%s, household_size=%s)",
                getattr(self.screen.white_label, "code", None),
                self.screen.household_size,
            )
            return 0
