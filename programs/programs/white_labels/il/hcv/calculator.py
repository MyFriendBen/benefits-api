import logging
from decimal import Decimal, ROUND_HALF_UP
from types import MappingProxyType

from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from programs.framework.base import Eligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages

logger = logging.getLogger(__name__)


class IlHcv(ProgramCalculator):
    """
    IL Housing Choice Voucher (Section 8) — an ongoing tenant-based rental subsidy,
    statewide across Illinois' 66 public housing agencies. MFB custom calculator.

    Eligibility: annual income (24 CFR 5.609, not raw gross) at or below HUD's
    published Very Low Income limit — 50% AMI — for the household's county and size.
    Federal rule allows five further routes above that limit, none of which holds
    statewide and none of which the screener can observe, so the modelled gate is
    deliberately narrowing: a household the screener rejects on income may still be
    admissible at its local agency. That is a Product-approved exception to the
    default-inclusive handling of data gaps, surfaced in the program description.

    Assumed met (unobservable): the six mandatory and ten discretionary denial
    grounds (24 CFR 982.553 / 982.552), the head's legal capacity to lease, and the
    student restriction of 24 CFR 5.612. **No asset or property gate is applied** —
    ``household_assets`` is not HUD's *net family assets*, so comparing it against
    the § 5.618 threshold would compare two different quantities, and § 5.618
    applicability varies by agency through 2026.

    Benefit value: monthly HAP = min(payment standard, gross rent) − total tenant
    payment, floored, annualized. Two inputs are MFB statewide estimation
    conventions rather than sourced rules, because MFB does not capture the
    administering agency: the payment standard (100% of the metro/county FMR) and
    the voucher bedroom size (one bedroom per two people). Minimum rent is modelled
    at $0, since the § 5.630(b)(1) hardship exemption is mandatory and unobservable.

    Not modelled (Benefit Value only, not eligibility): the utility allowance, the
    medical and child care deductions, the welfare-rent floor, ZIP-banded payment
    standards, and mixed-family proration — the payment is computed unprorated.
    """

    program_code = "il_hcv"

    ami_percent = "50%"
    # HUD's published CY2026 values, not the un-indexed § 5.611(a) bases of $480/$525.
    # Larger deductions mean a lower tenant payment and a higher subsidy, so these are
    # the inclusive choice where Illinois agencies differ on which figures they apply.
    dependent_deduction_annual = 500
    elderly_disabled_deduction_annual = 550
    min_rent_monthly = 0
    min_elderly_age = 62

    # Household size → voucher bedroom size: one bedroom per two people, rounded up.
    # An MFB statewide convention — every captured Illinois agency rule departs from
    # it upward, so it under-counts bedrooms and understates the subsidy.
    BEDROOM_MAP = MappingProxyType({1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4})

    #: Head, co-head or spouse — the members who are never dependents, and whose age
    #: or disability makes the household an elderly or disabled family (24 CFR 5.403).
    #: MFB has no co-head, so ``domesticPartner`` stands in for one.
    HEAD_RELATIONSHIPS = ("headOfHousehold", "spouse", "domesticPartner")

    #: Income types excluded from annual income for every member, whoever receives
    #: them: workers' compensation, per 24 CFR 5.609(b)(5).
    EXCLUDED_INCOME_TYPES = ("workersComp",)

    FOSTER_RELATIONSHIPS = ("fosterChild",)

    dependencies = (
        "income_amount",
        "income_frequency",
        "household_size",
        "county",
        "zipcode",
        "age",
        "relationship",
    )

    def _year_period(self) -> str:
        if self.program.year is None:
            raise HudIncomeClientError("Program year not configured")
        return self.program.year.period

    def _is_head_or_spouse(self, member) -> bool:
        return member.relationship in self.HEAD_RELATIONSHIPS

    def _is_minor(self, member) -> bool:
        """A member known to be under 18. An unknown age is treated as an adult, so
        an income exclusion is never applied on a guess."""
        return member.age is not None and member.age < 18

    def _countable_earned_income(self, member, earned: float) -> float:
        """
        A member's earned income after the two age- and study-dependent exclusions.
        Both attach to a person rather than to an income type, which is why annual
        income cannot be taken from a single screen-level ``calc_gross_income`` call.
        """
        # § 5.609(b)(3): earned income of a child under 18 is excluded entirely. The
        # head or spouse contributes in full whatever their age (§ 5.609(a)(1)).
        if self._is_minor(member) and not self._is_head_or_spouse(member):
            return 0.0

        # § 5.609(b)(14): a dependent full-time student's earned income counts only
        # up to the dependent-deduction amount; the excess is excluded.
        if member.student_full_time and not self._is_head_or_spouse(member):
            return min(earned, float(self.dependent_deduction_annual))

        return earned

    def _annual_income(self) -> float:
        """
        Annual income as 24 CFR 5.609 defines it — the quantity both the income gate
        and the value computation run on, not raw gross income.
        """
        total = 0.0
        for member in self.screen.household_members.all():
            # § 5.609(b)(8): a foster child's or foster adult's income is excluded.
            # They stay in household_size and keep their dependent deduction — see
            # the foster/kinship divergence recorded in the spec.
            if member.relationship in self.FOSTER_RELATIONSHIPS:
                continue

            earned = member.calc_gross_income("yearly", ["earned"], exclude=self.EXCLUDED_INCOME_TYPES)
            unearned = member.calc_gross_income("yearly", ["unearned"], exclude=self.EXCLUDED_INCOME_TYPES)

            # § 5.609(a)(1): unearned income counts for a dependent under 18 too.
            total += unearned + self._countable_earned_income(member, earned)
        return total

    def _effective_household_size(self):
        """A pregnant person living alone is a two-person family (24 CFR 982.402(b)(5)).
        Under the ``⌈n/2⌉`` bedroom map this changes no bedroom count — 1 and 2 both map
        to 1BR — but the rule is applied so a future map change stays correct."""
        if self.screen.household_size == 1:
            head = self.screen.get_head()
            if head is not None and head.pregnant:
                return 2
        return self.screen.household_size

    def _estimate_bedrooms(self) -> int:
        # A size outside 1–8 falls to 4BR, the largest published FMR bedroom count.
        return self.BEDROOM_MAP.get(self._effective_household_size(), 4)

    def _count_dependents(self) -> int:
        """
        Dependents per 24 CFR 5.603: a member other than the head or spouse who is
        under 18, has a disability, or is a full-time student. Foster children are
        **retained** here, departing from the federal text — MFB's single
        ``fosterChild`` value conflates foster placement with kinship care, and a
        kinship-care child is an ordinary dependent.
        """
        count = 0
        for member in self.screen.household_members.all():
            if self._is_head_or_spouse(member):
                continue
            if self._is_minor(member) or member.has_disability() or member.student_full_time:
                count += 1
        return count

    def _is_elderly_or_disabled_family(self) -> bool:
        """A family whose head, co-head, spouse or sole member is at least 62 or is a
        person with a disability (24 CFR 5.403)."""
        for member in self.screen.household_members.all():
            if not self._is_head_or_spouse(member):
                continue
            if (member.age is not None and member.age >= self.min_elderly_age) or member.has_disability():
                return True
        return False

    def _adjusted_income(self, annual_income: float) -> Decimal:
        """Annual income less the two modelled mandatory deductions, floored at zero
        (24 CFR 5.611(a))."""
        deductions = self._count_dependents() * self.dependent_deduction_annual
        if self._is_elderly_or_disabled_family():
            deductions += self.elderly_disabled_deduction_annual

        return max(Decimal(0), Decimal(str(annual_income)) - Decimal(deductions))

    def _total_tenant_payment(self, annual_income: float, annual_adjusted: Decimal) -> int:
        """
        The highest of 30% of monthly adjusted income, 10% of monthly income and the
        minimum rent, rounded to the nearest dollar **half-up** per the Form HUD-50058
        instructions (24 CFR 5.628(a)).

        Each prong is computed from the annual figure — 30% of a monthly amount is the
        annual over 40, and 10% is the annual over 120 — so an exact half-dollar stays
        exact instead of landing a hair under it. A float ``0.3 * (47540 / 12)`` gives
        1188.4999999999998 and rounds the wrong way; ``Decimal(47540) / 40`` gives
        1188.5 and rounds to 1189. Python's ``round()`` is banker's rounding and would
        also give 1188, so it is not used.
        """
        thirty_percent_monthly_adjusted = annual_adjusted / 40
        ten_percent_monthly_income = Decimal(str(annual_income)) / 120

        ttp = max(
            thirty_percent_monthly_adjusted,
            ten_percent_monthly_income,
            Decimal(self.min_rent_monthly),
        )
        return int(ttp.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def _gross_rent_proxy(self, payment_standard: int) -> float:
        """
        The household's reported rent stands in for the assisted unit's gross rent,
        falling back to the payment standard when no rent is reported — a household
        that is homeless, doubled up or living rent-free, for whom the standard arm
        governs anyway.

        ``mortgage`` is deliberately excluded: gross rent is rent to owner plus the
        utility allowance (24 CFR 982.4), and an owner's mortgage payment is not a
        proxy for the rent of a future tenant-based voucher unit.
        """
        reported_rent = self.screen.calc_expenses("monthly", ["rent"])
        return reported_rent if reported_rent > 0 else float(payment_standard)

    def household_eligible(self, e: Eligibility):
        # Criterion 1: annual income at or below HUD's Very Low Income limit for the
        # household's own county and size. A HUD lookup failure must never raise out
        # of the calculator and break the whole eligibility run.
        try:
            annual_income = int(self._annual_income())

            if self.screen.household_size is None:
                # No size means no limit to compare against. Passed inclusively rather
                # than compared — normally unreachable, since a null household_size is
                # a missing dependency and the program is not calculated at all.
                return

            income_limit = hud_client.get_screen_il_ami(self.screen, self.ami_percent, self._year_period())
            e.condition(annual_income <= income_limit, messages.income(annual_income, income_limit))
        except HudIncomeClientError:
            # Expected when HUD data is unavailable (API down, county not found, size
            # outside 1-8, year unconfigured) — not eligible, without noise.
            e.condition(False, messages.income_limit_unknown())
        except Exception:
            # Unexpected failure — still degrade to not eligible rather than raise, so
            # one program cannot 500 the whole eligibility response, and log it.
            logger.exception(
                "IlHcv.household_eligible income check failed unexpectedly (white_label=%s, household_size=%s)",
                getattr(self.screen.white_label, "code", None),
                self.screen.household_size,
            )
            e.condition(False, messages.income_limit_unknown())

    def household_value(self) -> int:
        try:
            annual_income = self._annual_income()
            annual_adjusted = self._adjusted_income(annual_income)
            ttp = self._total_tenant_payment(annual_income, annual_adjusted)

            payment_standard = hud_client.get_screen_payment_standard(
                self.screen, self._estimate_bedrooms(), self._year_period()
            )
            gross_rent = self._gross_rent_proxy(payment_standard)

            # 24 CFR 982.505(b): the payment is the lower of the two arms, less the
            # tenant payment. The payment standard is taken at the family unit size.
            hap = max(0.0, min(float(payment_standard), gross_rent) - ttp)

            # Floored at $1, not $0: a household whose rent sits below its own tenant
            # payment is genuinely eligible but nets no subsidy, and the frontend drops
            # any program whose value is not greater than zero. A nominal dollar keeps
            # it visible to exactly the people it applies to.
            return max(1, int(hap * 12))
        except HudIncomeClientError:
            # Expected when HUD data is unavailable — degrade to $0 without noise. This
            # is a value we could not compute rather than one that came out at zero, so
            # it is not floored: hiding the program is the honest outcome.
            return 0
        except Exception:
            # Unexpected bug in the value calculation — still degrade to $0 so one
            # program cannot 500 the whole eligibility response, but log it.
            logger.exception(
                "IlHcv.household_value failed unexpectedly (white_label=%s, household_size=%s)",
                getattr(self.screen.white_label, "code", None),
                self.screen.household_size,
            )
            return 0
