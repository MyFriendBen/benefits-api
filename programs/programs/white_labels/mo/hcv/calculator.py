import logging
from decimal import Decimal, ROUND_HALF_UP
from types import MappingProxyType

from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from programs.framework.base import Eligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages

logger = logging.getLogger(__name__)


class MoHcv(ProgramCalculator):
    """
    MO Housing Choice Voucher (Section 8) — a tenant-based rental subsidy,
    modelled on KsHcv and HAKC's (Kansas City) administrative plan for
    locally-set figures.

    Eligible: annual income at or below 50% AMI, after excluding a minor's
    earnings (unless head/spouse), a dependent student's earnings above the
    student deduction, workersComp income, and a foster child's income. No
    asset gate. Must not already hold a Section 8 voucher.

    Benefit: monthly HAP = min(payment standard, reported rent) − total
    tenant payment, annualized and floored at $1. Adjusted income subtracts
    a per-dependent deduction, a one-time elderly/disabled deduction, and
    medical/childcare deductions.

    St. Louis City households show $0 until MFB-2110 fixes county lookup.
    """

    program_code = "mo_hcv"

    ami_percent = "50%"
    dependent_deduction_annual = 480
    elderly_disabled_deduction_annual = 400
    min_rent_monthly = 50
    min_elderly_age = 62
    medical_deduction_floor_percent = Decimal("0.03")

    #: Head, co-head (domesticPartner), or spouse — never dependents, and
    #: whose age/disability sets the elderly-or-disabled flag.
    HEAD_RELATIONSHIPS = ("headOfHousehold", "spouse", "domesticPartner")

    #: Excluded from annual income for every member.
    EXCLUDED_INCOME_TYPES = ("workersComp",)

    #: Foster children's income is excluded, and they don't count as dependents.
    FOSTER_RELATIONSHIPS = ("fosterChild",)

    #: relationship -> generation, for the bedroom standard. An unmapped or
    #: unrecognized relationship falls to generation 0 (the head's).
    GENERATION_MAP = MappingProxyType(
        {
            "grandParent": 2,
            "parent": 1,
            "fosterParent": 1,
            "stepParent": 1,
            "headOfHousehold": 0,
            "spouse": 0,
            "domesticPartner": 0,
            "sisterOrBrother": 0,
            "stepSisterOrBrother": 0,
            "boyfriendOrGirlfriend": 0,
            "roommate": 0,
            "relatedOther": 0,
            "child": -1,
            "stepChild": -1,
            "fosterChild": -1,
            "grandChild": -2,
        }
    )

    #: HUD publishes no FMR above 4 bedrooms.
    MAX_BEDROOMS = 4

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

    @staticmethod
    def _age(member):
        """Age from `birth_year_month`, not the possibly-stale raw `age` field."""
        return member.calc_age()

    def _is_head_or_spouse(self, member) -> bool:
        return member.relationship in self.HEAD_RELATIONSHIPS

    def _is_minor(self, member) -> bool:
        """Unknown age is treated as an adult, so income is never excluded on a guess."""
        age = self._age(member)
        return age is not None and age < 18

    def _countable_earned_income(self, member, earned: float) -> float:
        """A member's earned income after the person-scoped exclusions: a foster
        child's income is excluded entirely, a minor's earnings are excluded
        unless they're the head or spouse, and a dependent student's earnings
        above the dependent deduction are excluded. Order matters — a member
        who is both a minor and a student must hit the minor branch first, or
        they lose the full exclusion."""
        if member.relationship in self.FOSTER_RELATIONSHIPS:
            return 0.0

        if self._is_minor(member) and not self._is_head_or_spouse(member):
            return 0.0

        if member.student_full_time and not self._is_head_or_spouse(member):
            return min(earned, float(self.dependent_deduction_annual))

        return earned

    def _annual_income(self) -> float:
        """Annual income after the exclusions above, aggregated per member —
        a single screen-level income call would apply one exclusion list to
        everyone instead of scoping it per person."""
        total = 0.0
        for member in self.screen.household_members.all():
            if member.relationship in self.FOSTER_RELATIONSHIPS:
                continue

            earned = member.calc_gross_income("yearly", ["earned"], exclude=self.EXCLUDED_INCOME_TYPES)
            unearned = member.calc_gross_income("yearly", ["unearned"], exclude=self.EXCLUDED_INCOME_TYPES)
            total += unearned + self._countable_earned_income(member, earned)
        return total

    def _generation_counts(self) -> dict:
        """Members grouped by generation, for the bedroom count. A pregnant
        sole applicant counts as two people (a notional member added to the
        child generation) — this only affects the bedroom count, not the
        household size used for the income test."""
        counts: dict = {}
        for member in self.screen.household_members.all():
            generation = self.GENERATION_MAP.get(member.relationship, 0)
            counts[generation] = counts.get(generation, 0) + 1

        if self.screen.household_size == 1:
            head = self.screen.get_head()
            if head is not None and head.pregnant:
                counts[-1] = counts.get(-1, 0) + 1

        return counts

    def _estimate_bedrooms(self) -> int:
        """One bedroom per two people within each occupied generation, capped
        at four."""
        counts = self._generation_counts()
        total_bedrooms = sum((count + 1) // 2 for count in counts.values())
        return min(self.MAX_BEDROOMS, total_bedrooms)

    def _count_dependents(self) -> int:
        """A dependent is any non-head member who is a minor, disabled, or a
        full-time student. Foster children never count."""
        count = 0
        for member in self.screen.household_members.all():
            if self._is_head_or_spouse(member):
                continue
            if member.relationship in self.FOSTER_RELATIONSHIPS:
                continue
            if self._is_minor(member) or member.has_disability() or member.student_full_time:
                count += 1
        return count

    def _is_elderly_or_disabled_family(self) -> bool:
        """True if the head, co-head, or spouse is 62+ or has a disability."""
        for member in self.screen.household_members.all():
            if not self._is_head_or_spouse(member):
                continue
            age = self._age(member)
            if (age is not None and age >= self.min_elderly_age) or member.has_disability():
                return True
        return False

    def _medical_deduction(self, annual_gross: Decimal) -> Decimal:
        """Unreimbursed medical expenses above 3% of income, for an elderly
        or disabled family only."""
        medical = Decimal(str(self.screen.calc_expenses("yearly", ["medical"])))
        floor = annual_gross * self.medical_deduction_floor_percent
        return max(Decimal(0), medical - floor)

    def _childcare_deduction(self) -> Decimal:
        """Childcare expenses, capped at the lowest-paid earner's included
        earned income when the household has earners (built from
        `_countable_earned_income`, so an excluded earner doesn't set the
        cap). Uncapped when there are no earners."""
        childcare = Decimal(str(self.screen.calc_expenses("yearly", ["childCare"])))

        earners = []
        for member in self.screen.household_members.all():
            earned = member.calc_gross_income("yearly", ["earned"], exclude=self.EXCLUDED_INCOME_TYPES)
            countable = self._countable_earned_income(member, earned)
            if countable > 0:
                earners.append(countable)

        if not earners:
            return childcare

        return min(childcare, Decimal(str(min(earners))))

    def _adjusted_income(self, annual_income: float) -> Decimal:
        """Annual income minus the dependent, elderly/disabled, medical, and
        childcare deductions, floored at zero."""
        annual_gross = Decimal(str(annual_income))
        elderly_or_disabled = self._is_elderly_or_disabled_family()

        deductions = Decimal(self._count_dependents() * self.dependent_deduction_annual)
        if elderly_or_disabled:
            deductions += Decimal(self.elderly_disabled_deduction_annual)
            deductions += self._medical_deduction(annual_gross)
        deductions += self._childcare_deduction()

        return max(Decimal(0), annual_gross - deductions)

    def _total_tenant_payment(self, annual_income: float, annual_adjusted: Decimal) -> int:
        """Highest of 30% of monthly adjusted income, 10% of monthly gross
        income, and the $50 minimum rent, rounded to the nearest dollar
        half-up (not Python's banker's-rounding `round()`)."""
        thirty_percent_monthly_adjusted = annual_adjusted / 40
        ten_percent_monthly_income = Decimal(str(annual_income)) / 120

        ttp = max(
            thirty_percent_monthly_adjusted,
            ten_percent_monthly_income,
            Decimal(self.min_rent_monthly),
        )
        return int(ttp.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def _gross_rent_proxy(self, payment_standard: int) -> float:
        """Reported rent stands in for the unit's gross rent, falling back to
        the payment standard when no rent is reported. Mortgage isn't counted
        as rent."""
        reported_rent = self.screen.calc_expenses("monthly", ["rent"])
        return reported_rent if reported_rent > 0 else float(payment_standard)

    def household_eligible(self, e: Eligibility):
        # Every screen has a household of at least one person.
        e.condition(self.screen.household_size is None or self.screen.household_size >= 1)

        # Don't show a household a voucher it already has.
        e.condition(
            not self.screen.has_base_benefit("section_8"),
            messages.must_not_have_benefit("a Housing Choice Voucher"),
        )

        # Income test against HUD's Very Low Income limit. A HUD lookup
        # failure degrades to not-eligible instead of raising, so one
        # program can't break eligibility for the whole screen.
        try:
            annual_income = int(self._annual_income())

            if self.screen.household_size is None:
                return

            income_limit = hud_client.get_screen_il_ami(self.screen, self.ami_percent, self._year_period())
            e.condition(annual_income <= income_limit, messages.income(annual_income, income_limit))
        except HudIncomeClientError:
            e.condition(False, messages.income_limit_unknown())
        except Exception:
            logger.exception(
                "MoHcv.household_eligible income check failed unexpectedly (white_label=%s, household_size=%s)",
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

            hap = max(0.0, min(float(payment_standard), gross_rent) - ttp)

            # Floored at $1: the frontend hides any program valued at $0, but
            # this household is still genuinely eligible.
            return max(1, int(hap * 12))
        except HudIncomeClientError:
            return 0
        except Exception:
            logger.exception(
                "MoHcv.household_value failed unexpectedly (white_label=%s, household_size=%s)",
                getattr(self.screen.white_label, "code", None),
                self.screen.household_size,
            )
            return 0
