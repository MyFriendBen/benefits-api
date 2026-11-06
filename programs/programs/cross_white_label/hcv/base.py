"""Housing Choice Voucher (Section 8) — MFB federal base."""

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar, Optional

from integrations.clients.hud_income_limits import HudIncomeClientError, hud_client
from integrations.clients.hud_income_limits.client import Section8AmiPercent
from programs.framework.base import Eligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages
from screener.models import HouseholdMember

logger = logging.getLogger(__name__)

#: The head and their spouse. A domestic partner is not a spouse: they count as any other
#: adult does, and can be a dependent.
HEAD_OR_SPOUSE = frozenset({"headOfHousehold", "spouse"})

#: Members who are never dependents besides the head and spouse (24 CFR 5.603, "Dependent").
NOT_DEPENDENT = HEAD_OR_SPOUSE | {"fosterChild"}

#: A child of the head, for the student bar's has-a-child exemption.
CHILD_OF_HEAD = frozenset({"child", "stepChild"})

#: HUD publishes FMRs up to four bedrooms; each bedroom past four adds 15% of the
#: four-bedroom figure (FMR schedule, note 1).
MAX_PUBLISHED_BEDROOMS = 4
EXTRA_BEDROOM_INCREMENT = Decimal("0.15")


def _exact(amount: float) -> Decimal:
    """A screener dollar figure as an exact decimal.

    `calc_gross_income` and `calc_expenses` sum in float, so a whole-dollar total can arrive a
    fraction of a cent off, and an income exactly at HUD's limit must not drift over it.
    Rounding to a millionth removes the drift and keeps every real amount intact.
    """
    return Decimal(str(round(amount, 6)))


def _round_half_up(amount: Decimal) -> int:
    """Round to the dollar, half up. Python's `round()` rounds an exact half to even."""
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class HousingChoiceVoucher(ProgramCalculator, abstract=True):
    """
    The federal Housing Choice Voucher rules, computed in our own code (24 CFR 982 and
    24 CFR 5 subparts E and F).

    Eligibility, all household-level:

    - A family: one person or more.
    - Annual income at or below HUD's Section 8 limit for the household's county and size.
      HUD offers two routes: very low income (50% of area median), or low income (80%) for a
      family in a special category (continuously assisted, displaced by a prepayment, HOPE or
      resident homeownership). The screener can't see the categories, so each state decides
      whether to offer the 80% route with them unevaluated (``special_category_assumed``) or
      to test 50% alone.
    - Net assets at or below the state's limit, read from the one asset total the screener
      collects.
    - No member barred as a student: under 24, enrolled half time or more, unmarried, with no
      child and not living with a parent. ``student_full_time`` is the half-time question;
      blank means not barred.

    Annual income counts every income of each adult, the head and the spouse, plus a minor's
    unearned income. A dependent student's earnings count only up to
    ``student_earnings_cap``. Workers' compensation never counts.

    Value: the monthly payment standard less the total tenant payment, which is the highest of
    30% of monthly adjusted income, 10% of monthly income and the minimum rent, rounded half
    up. Adjusted income takes off the dependent, elderly or disabled, medical (above 10% of
    income, elderly or disabled families only) and child care (a member under 13)
    deductions, plus any the state adds. An eligible household is floored at $1 a year so
    it stays visible, since the results page hides a program worth $0.

    The payment standard is HUD's FMR, or the ZIP's Small Area FMR in a mandatory-SAFMR metro,
    for the voucher size the state's subsidy standards give the household. The leased unit's
    rent is unknown at screening, so the payment standard stands in for it. Mixed-family
    proration is taken as 1: the screener records one immigration status for the household.

    Each state sets the values below. The base spec is
    ``programs/cross_white_label/hcv/base/hcv_base_spec.md`` in program-ops.
    """

    # --- Set by each state ------------------------------------------------------------------

    #: Net assets above this fail (24 CFR 5.618(a)(1)(i), as the state's agency applies it).
    net_assets_limit_amount: ClassVar[int]
    #: A dependent full-time student's earnings above this don't count (24 CFR 5.609(b)(14)).
    student_earnings_cap: ClassVar[int]
    #: Per dependent, and once for an elderly or disabled family (24 CFR 5.611(a)(1)-(2)).
    dependent_deduction: ClassVar[int]
    elderly_disabled_deduction: ClassVar[int]
    #: Monthly minimum rent, up to $50 (24 CFR 5.630(a)(2)).
    minimum_rent: ClassVar[int]
    #: Whether the 80% special-category route is offered with its categories unevaluated.
    special_category_assumed: ClassVar[bool]
    #: `(bedrooms, smallest household, largest household)` rows from the agency's plan.
    subsidy_standards: ClassVar[tuple[tuple[int, int, int], ...]]
    #: HUD fiscal year of the FMRs the payment standard reads. FMRs publish each October,
    #: income limits each spring, so the two years differ for half of each year.
    payment_standard_year: ClassVar[int]

    # --- Federal values ---------------------------------------------------------------------

    medical_expense_threshold = Decimal("0.10")
    adjusted_income_share = Decimal("0.30")
    gross_income_share = Decimal("0.10")
    adult_age = 18
    elderly_age = 62
    student_bar_age = 24
    child_care_age = 13
    excluded_income_types = ("workersComp",)

    dependencies = (
        "income_type",
        "income_amount",
        "income_frequency",
        "household_size",
        "household_assets",
        "county",
        "zipcode",
        "age",
        "relationship",
    )

    # --- Eligibility ------------------------------------------------------------------------

    def household_eligible(self, e: Eligibility) -> None:
        e.condition(self.screen.household_size is not None and self.screen.household_size >= 1)

        self._income_condition(e)

        assets = self.screen.household_assets if self.screen.household_assets is not None else 0
        e.condition(assets <= self.net_assets_limit_amount, messages.assets(self.net_assets_limit_amount))

        members = list(self.screen.household_members.all())
        e.condition(not any(self._is_barred_student(member, members) for member in members))

    def _income_condition(self, e: Eligibility) -> None:
        """Annual income against HUD's limit. A failed HUD lookup never raises out of the
        calculator: the household is not eligible, with the limit unknown."""
        try:
            annual_income = _round_half_up(self.annual_income())
            limit = hud_client.get_screen_il_ami(self.screen, self.income_limit_percent(), self._income_limit_year())
            e.condition(annual_income <= limit, messages.income(annual_income, limit))
        except HudIncomeClientError:
            e.condition(False, messages.income_limit_unknown())
        except Exception:
            logger.exception(
                "%s income check failed unexpectedly (household_size=%s)",
                type(self).__name__,
                self.screen.household_size,
            )
            e.condition(False, messages.income_limit_unknown())

    def income_limit_percent(self) -> Section8AmiPercent:
        """HUD's low-income row when the special-category route is offered, since every
        family under the very-low-income limit is under it too; else very low income."""
        return "80%" if self.special_category_assumed else "50%"

    def _income_limit_year(self) -> str:
        if self.program.year is None:
            raise HudIncomeClientError("Program year not configured")
        return self.program.year.period

    def _is_barred_student(self, member: HouseholdMember, members: list[HouseholdMember]) -> bool:
        """24 CFR 5.612, as the screener can see it. Relationships run to the head, so only
        the head and the head's spouse, child or parent can be linked to anyone."""
        if not member.student_full_time:
            return False

        age = member.calc_age()
        if age is None or age >= self.student_bar_age:
            return False

        is_head = member.relationship == "headOfHousehold"
        others = [other.relationship for other in members if other is not member]

        married = member.relationship == "spouse" or (is_head and "spouse" in others)
        lives_with_parent = member.relationship == "child" or (is_head and "parent" in others)
        has_child = member.relationship in HEAD_OR_SPOUSE and any(r in CHILD_OF_HEAD for r in others)

        return not (married or lives_with_parent or has_child)

    # --- Income -----------------------------------------------------------------------------

    def _is_adult_or_head(self, member: HouseholdMember) -> bool:
        """Whose income counts in full. An unknown age is read as an adult, so no income is
        left out on a guess."""
        if member.relationship in HEAD_OR_SPOUSE:
            return True
        age = member.calc_age()
        return age is None or age >= self.adult_age

    def annual_income(self) -> Decimal:
        """Annual income (24 CFR 5.609): an adult's, the head's and the spouse's income from
        every source, and a minor's unearned income; a dependent student's earnings count up
        to the cap."""
        total = Decimal(0)
        for member in self.screen.household_members.all():
            earned = _exact(member.calc_gross_income("yearly", ["earned"], exclude=self.excluded_income_types))
            unearned = _exact(member.calc_gross_income("yearly", ["unearned"], exclude=self.excluded_income_types))

            if not self._is_adult_or_head(member):
                earned = Decimal(0)
            elif member.student_full_time and member.relationship not in HEAD_OR_SPOUSE:
                earned = min(earned, Decimal(self.student_earnings_cap))

            total += earned + unearned
        return total

    # --- Value ------------------------------------------------------------------------------

    def household_value(self) -> int:
        try:
            monthly = self.payment_standard() - self.total_tenant_payment()
            # An eligible household is floored at $1 a year: a payment that works out to $0 or
            # less would hide the program on the results page.
            return max(1, monthly * 12)
        except HudIncomeClientError:
            # The payment standard couldn't be read. That's an unknown value, not a $0 one, so
            # the program is hidden rather than floored.
            return 0
        except Exception:
            logger.exception(
                "%s value failed unexpectedly (household_size=%s)",
                type(self).__name__,
                self.screen.household_size,
            )
            return 0

    def total_tenant_payment(self) -> int:
        """24 CFR 5.628(a). Each share is taken from the annual figure (30% of a twelfth is a
        fortieth), so an exact half-dollar stays exact before it rounds."""
        annual_income = self.annual_income()
        adjusted = self.adjusted_income(annual_income)
        return _round_half_up(
            max(
                self.adjusted_income_share * adjusted / 12,
                self.gross_income_share * annual_income / 12,
                Decimal(self.minimum_rent),
            )
        )

    def adjusted_income(self, annual_income: Decimal) -> Decimal:
        """Annual adjusted income (24 CFR 5.611), floored at $0."""
        deductions = Decimal(self.dependent_deduction * self.dependents())
        deductions += self.child_care_deduction()
        deductions += self.additional_deductions()

        if self.is_elderly_or_disabled_family():
            deductions += self.elderly_disabled_deduction
            medical = _exact(self.screen.calc_expenses("yearly", ["medical"]))
            deductions += max(Decimal(0), medical - self.medical_expense_threshold * annual_income)

        return max(Decimal(0), annual_income - deductions)

    def dependents(self) -> int:
        """Members other than the head, the spouse and a foster child who are under 18, have a
        disability or are students (24 CFR 5.603)."""
        count = 0
        for member in self.screen.household_members.all():
            if member.relationship in NOT_DEPENDENT:
                continue
            age = member.calc_age()
            if (age is not None and age < self.adult_age) or member.has_disability() or member.student_full_time:
                count += 1
        return count

    def is_elderly_or_disabled_family(self) -> bool:
        """The head or spouse is 62 or older or has a disability (24 CFR 5.403)."""
        for member in self.screen.household_members.all():
            if member.relationship not in HEAD_OR_SPOUSE:
                continue
            age = member.calc_age()
            if (age is not None and age >= self.elderly_age) or member.has_disability():
                return True
        return False

    def child_care_deduction(self) -> Decimal:
        """Every `childCare` expense, where any member is under 13 (24 CFR 5.611(a)(4))."""
        has_young_child = any(
            (age := member.calc_age()) is not None and age < self.child_care_age
            for member in self.screen.household_members.all()
        )
        if not has_young_child:
            return Decimal(0)
        return _exact(self.screen.calc_expenses("yearly", ["childCare"]))

    def additional_deductions(self) -> Decimal:
        """Deductions the state's agency adds in its plan (24 CFR 5.611(b)). None by default."""
        return Decimal(0)

    # --- Payment standard -------------------------------------------------------------------

    def voucher_size(self) -> Optional[int]:
        """The fewest bedrooms whose subsidy-standard row covers the household's size."""
        size = self.screen.household_size
        fits = [bedrooms for bedrooms, smallest, largest in self.subsidy_standards if smallest <= size <= largest]
        return min(fits) if fits else None

    def payment_standard(self) -> int:
        """HUD's FMR, or the Small Area FMR in a mandatory-SAFMR metro, for the voucher size;
        each bedroom past four adds 15% of the four-bedroom figure."""
        bedrooms = self.voucher_size()
        if bedrooms is None:
            raise HudIncomeClientError(f"No voucher size for a household of {self.screen.household_size}")

        rent = hud_client.get_screen_payment_standard(
            self.screen, min(bedrooms, MAX_PUBLISHED_BEDROOMS), self.payment_standard_year
        )
        extra_bedrooms = max(0, bedrooms - MAX_PUBLISHED_BEDROOMS)
        return _round_half_up(Decimal(rent) * (1 + EXTRA_BEDROOM_INCREMENT * extra_bedrooms))
