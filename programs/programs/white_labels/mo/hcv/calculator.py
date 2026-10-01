import logging
from decimal import Decimal, ROUND_HALF_UP
from types import MappingProxyType

from integrations.clients.hud_income_limits import hud_client, HudIncomeClientError
from programs.framework.base import Eligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages

logger = logging.getLogger(__name__)


class MoHcv(ProgramCalculator):
    """
    MO Housing Choice Voucher (Section 8) — an ongoing tenant-based rental subsidy,
    statewide across Missouri's 45 public housing agencies. MFB custom calculator,
    modelled on ``KsHcv``'s structure and the Housing Authority of Kansas City,
    Missouri (HAKC) HCV Administrative Plan effective 12/2025 for every locally-set
    figure (minimum rent, dependent/elderly deductions, bedroom-size standard).

    Eligibility (plain conjunction of four criteria): annual income (24 CFR 5.609,
    not raw gross) at or below HUD's published Very Low Income limit — 50% AMI —
    for the household's own county and size; household size at least one (trivial);
    an eligible citizenship/immigration status, handled entirely through
    ``legal_status_required`` in the program config, with no calculator branch; and,
    uniquely among the shipped HCV siblings, not already holding Section 8 —
    ``self.screen.has_base_benefit("section_8")``. Four income exclusions apply to
    the annual-income figure both the income gate and the value calculation run on:
    a minor's earned income (unless they are the head or spouse), a dependent
    full-time student's earnings above the dependent-deduction amount, all
    ``workersComp`` income, and all income of a ``fosterChild``-relationship member.

    Assumed met (unobservable): the criminal/eviction/debt denial grounds, the
    § 5.612 student restriction, HOTMA's net-asset and real-property limitation
    (not enforced at HAKC before 2027-01-01), the imputed-asset-return rule, and
    § 5.520's mixed-family proration. **No asset or property gate is applied** for
    the same reason as the shipped siblings: ``household_assets`` is not HUD's
    *net family assets*.

    Benefit value: monthly HAP = min(payment standard, gross rent proxy) − total
    tenant payment (TTP), floored at $1 for an eligible household, annualized. The
    payment standard is 100% of the FY2026 FMR — or the ZIP-level Small Area FMR in
    a mandatory-SAFMR metro — read through the shared ``hud_client``. The gross-rent
    proxy reads ``["rent"]`` only, excluding ``mortgage``, matching ``IlHcv`` and
    ``KsHcv`` rather than ``TxHcv``/``WaHcv``. TTP is the highest of 30% of monthly
    adjusted income, 10% of monthly (countable) gross income, and HAKC's $50
    minimum rent — the federal ceiling, and the figure Missouri shares only with
    ``WaHcv``. Adjusted income subtracts four HAKC Chapter 6.A (pre-HOTMA) mandatory
    deductions: $480 per dependent, $400 once for an elderly-or-disabled family, an
    unreimbursed health/medical deduction above a 3%-of-income floor for an elderly
    or disabled family, and a childcare deduction capped — where the household has
    earners — at the lowest-paid earner's *included* (post-exclusion) earned
    income. Missouri is the only shipped HCV white label modelling the last two:
    every sibling omits them as a documented simplification.

    Missouri departs from the shipped siblings on two further points cited
    explicitly in this program's spec. First, a ``fosterChild``-relationship member
    is **excluded** from the dependent count (§ 5.603's own text), where ``IlHcv``,
    ``KsHcv`` and ``WaHcv`` all retain foster children as dependents — only
    ``TxHcv`` agrees. Second, the voucher bedroom size is **not** a household-size
    lookup: HAKC assigns one bedroom per two people *within each occupied
    generation* (``relationship`` mapped to a generation from +2 to −2), summed and
    capped at four bedrooms — a composition rule that can diverge sharply from a
    plain size-based map for a multigenerational household. A pregnant sole
    applicant is still modelled as a two-person family for the bedroom count only
    (24 CFR 982.402(b)(5)), with the notional member placed in the child
    generation.

    Known data/implementation gap, out of scope for this calculator: ``Screen.county``
    stores the literal ``"St. Louis City"`` for the 27 St. Louis-city ZIP codes,
    which ``hud_client._get_entity_id`` cannot resolve until MFB-2110 lands —
    St. Louis-city households will present as not eligible, $0, until that fix
    ships. ``MoHcv`` deliberately adds **no** county override for this, per the
    program spec: a fixed override would misroute every other Missouri county.
    """

    program_code = "mo_hcv"

    ami_percent = "50%"
    # HAKC HCV Administrative Plan Chapter 6.A (pre-HOTMA, in force at HAKC before its
    # own 2027-01-01 HOTMA 102/104 compliance date) — $480/$400, not the CY2026
    # inflation-adjusted $500/$550 pair `il_hcv` and `ks_hcv` carry, and not the
    # un-indexed post-HOTMA $480/$525 pair `tx_hcv`/`wa_hcv` carry.
    dependent_deduction_annual = 480
    elderly_disabled_deduction_annual = 400
    # HAKC's stated local minimum rent and the § 5.630(a)(2) federal ceiling — the
    # top of the permitted range, shared only with `wa_hcv` among the siblings.
    min_rent_monthly = 50
    min_elderly_age = 62
    # § 5.611(a)(3)(i)'s pre-HOTMA floor on the health/medical deduction — three
    # percent of annual income, not the ten percent the post-HOTMA eCFR text now
    # carries (that increase does not bind at HAKC until its own compliance date).
    medical_deduction_floor_percent = Decimal("0.03")

    #: Head, co-head or spouse — the members who are never dependents, and whose age
    #: or disability makes the household an elderly or disabled family (24 CFR 5.403).
    #: MFB has no co-head, so ``domesticPartner`` stands in for one, matching the IL
    #: and KS siblings. The tuple decides four rules: the dependent count, the
    #: § 5.609(b)(3) minor-earner exclusion, the § 5.609(b)(14) dependent-student
    #: exclusion, and the § 5.403 elderly-or-disabled flag.
    HEAD_RELATIONSHIPS = ("headOfHousehold", "spouse", "domesticPartner")

    #: Income types excluded from annual income for every member, whoever receives
    #: them: workers' compensation, per 24 CFR 5.609(b)(5).
    EXCLUDED_INCOME_TYPES = ("workersComp",)

    #: § 5.609(b)(8) excludes a foster child's income entirely, and § 5.603 excludes
    #: them from the *dependent* definition too — departing from `IlHcv`, `KsHcv`
    #: and `WaHcv`, which all retain foster children as dependents. Only `TxHcv`
    #: agrees with Missouri here.
    FOSTER_RELATIONSHIPS = ("fosterChild",)

    #: `relationship` → generation offset, read for the bedroom standard only.
    #: A member whose `relationship` is null, unrecognised, or one of the three
    #: values that carry no real generational distance (`relatedOther`, `roommate`,
    #: `boyfriendOrGirlfriend`) falls to generation 0, the head's own generation —
    #: the reading that yields the lower, more conservative bedroom count.
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

    #: HAKC's subsidy standard is capped at four bedrooms — HUD publishes no FMR
    #: above that, and `hud_client._validate_bedrooms` rejects anything outside
    #: 0–4. Reachable from two occupied generations upward in a large household.
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
        """A member's age against the screen's reference date, from
        ``birth_year_month`` where it is set — never the raw, possibly-stale ``age``
        field. ``calc_age()`` falls back to the raw field when no birth date is
        recorded, so the result is still ``None`` for a member with neither."""
        return member.calc_age()

    def _is_head_or_spouse(self, member) -> bool:
        return member.relationship in self.HEAD_RELATIONSHIPS

    def _is_minor(self, member) -> bool:
        """A member known to be under 18. An unknown age is treated as an adult, so
        an income exclusion is never applied on a guess."""
        age = self._age(member)
        return age is not None and age < 18

    def _countable_earned_income(self, member, earned: float) -> float:
        """
        A member's earned income after the three person-scoped exclusions that
        attach to a person rather than to an income type: § 5.609(b)(8) (a foster
        child's income is excluded entirely, checked first since it is the
        strongest and unconditional exclusion), § 5.609(b)(3) (a minor's earned
        income, unless they are the head or spouse), and § 5.609(b)(14) (a
        dependent full-time student's earnings above the dependent-deduction
        amount). The minor branch must run before the student branch: a member who
        is both under 18 and a full-time student is excluded in full under (b)(3),
        not capped at the dependent-deduction amount under (b)(14) — § 5.609(b)'s
        lead-in makes the exclusions a union, not a sequence, so an amount (b)(3)
        already excludes cannot be re-included by (b)(14).
        """
        if member.relationship in self.FOSTER_RELATIONSHIPS:
            return 0.0

        if self._is_minor(member) and not self._is_head_or_spouse(member):
            return 0.0

        if member.student_full_time and not self._is_head_or_spouse(member):
            return min(earned, float(self.dependent_deduction_annual))

        return earned

    def _annual_income(self) -> float:
        """
        Annual income as 24 CFR 5.609 defines it, § 5.609(b)-adjusted — the
        quantity both the income gate and the value computation (including the
        TTP's 10%-of-gross-income prong and the (a)(3) medical floor's base) run
        on, not raw gross income.
        """
        total = 0.0
        for member in self.screen.household_members.all():
            # § 5.609(b)(8): all of a foster child's income is excluded, earned and
            # unearned alike — handled here as an early skip rather than inside
            # `_countable_earned_income` alone, since that only reaches earned
            # income.
            if member.relationship in self.FOSTER_RELATIONSHIPS:
                continue

            earned = member.calc_gross_income("yearly", ["earned"], exclude=self.EXCLUDED_INCOME_TYPES)
            unearned = member.calc_gross_income("yearly", ["unearned"], exclude=self.EXCLUDED_INCOME_TYPES)

            # § 5.609(a)(1): unearned income counts for a dependent under 18 too.
            total += unearned + self._countable_earned_income(member, earned)
        return total

    def _generation_counts(self) -> dict:
        """Household members grouped by generation, read from `relationship`, plus
        the § 982.402(b)(5) notional member for a pregnant sole applicant.

        Unlike the income-limit comparison, which always uses the real
        `household_size`, this notional member exists only for the bedroom count —
        the regulation's lead-in scopes the whole paragraph to family unit size.
        """
        counts: dict = {}
        for member in self.screen.household_members.all():
            generation = self.GENERATION_MAP.get(member.relationship, 0)
            counts[generation] = counts.get(generation, 0) + 1

        if self.screen.household_size == 1:
            head = self.screen.get_head()
            if head is not None and head.pregnant:
                # The notional second member sits in the child generation, so a
                # pregnant sole applicant becomes two bedrooms (1+1), not one.
                counts[-1] = counts.get(-1, 0) + 1

        return counts

    def _estimate_bedrooms(self) -> int:
        """
        One bedroom per two people *within each occupied generation*, summed and
        capped at four. This is HAKC's composition-based subsidy standard, not a
        household-size lookup — it can diverge sharply from `BEDROOM_MAP`-style
        siblings for a multigenerational household (see Scenarios 12, 20, 22, 29,
        31 and 34 in the program spec).
        """
        counts = self._generation_counts()
        total_bedrooms = sum((count + 1) // 2 for count in counts.values())
        return min(self.MAX_BEDROOMS, total_bedrooms)

    def _count_dependents(self) -> int:
        """
        Dependents per 24 CFR 5.603: a member other than the head, co-head or
        spouse who is under 18, has a disability, or is a full-time student.
        Foster children are **excluded** here, following § 5.603's own text —
        departing from `IlHcv`, `KsHcv` and `WaHcv`, which all retain them; only
        `TxHcv` agrees.
        """
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
        """A family whose head, co-head, spouse or sole member is at least 62 or is
        a person with a disability (24 CFR 5.403). A family-level flag taken once,
        not a per-member count — and read through ``has_disability()``, which ORs
        ``disabled``, ``visually_impaired`` and ``long_term_disability``."""
        for member in self.screen.household_members.all():
            if not self._is_head_or_spouse(member):
                continue
            age = self._age(member)
            if (age is not None and age >= self.min_elderly_age) or member.has_disability():
                return True
        return False

    def _medical_deduction(self, annual_gross: Decimal) -> Decimal:
        """§ 5.611(a)(3)(i): unreimbursed health and medical care expenses above
        three percent of annual (countable) income, for an elderly or disabled
        family only — the caller gates on that flag. ``"medical"`` is a leaf key,
        not a category path."""
        medical = Decimal(str(self.screen.calc_expenses("yearly", ["medical"])))
        floor = annual_gross * self.medical_deduction_floor_percent
        return max(Decimal(0), medical - floor)

    def _childcare_deduction(self) -> Decimal:
        """§ 5.611(a)(4): reasonable childcare expenses, capped — where the
        household has earners — at the lowest-paid earner's employment income that
        is *included* in annual income, per HAKC § 6-II.F. The earner list is built
        from `_countable_earned_income`, not a raw per-member `calc_gross_income`
        call, so a member whose earnings § 5.609(b)(3), (b)(8) or (b)(14) exclude
        (in whole or in part) is not an earner, or is one at a reduced figure. A
        household with no included earned income cannot be on the work branch and
        takes the deduction uncapped. ``"childCare"`` is a leaf key; `childSupport`
        is a different leaf and is not part of this deduction.
        """
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
        """
        Annual (countable) income less all four § 5.611(a) mandatory deductions
        HAKC's Chapter 6.A applies, floored at zero: $480 per dependent, $400 once
        for an elderly-or-disabled family, the (a)(3)(i) health/medical deduction
        and the (a)(4) childcare deduction — the last two of which no shipped HCV
        sibling models.
        """
        annual_gross = Decimal(str(annual_income))
        elderly_or_disabled = self._is_elderly_or_disabled_family()

        deductions = Decimal(self._count_dependents() * self.dependent_deduction_annual)
        if elderly_or_disabled:
            deductions += Decimal(self.elderly_disabled_deduction_annual)
            deductions += self._medical_deduction(annual_gross)
        deductions += self._childcare_deduction()

        return max(Decimal(0), annual_gross - deductions)

    def _total_tenant_payment(self, annual_income: float, annual_adjusted: Decimal) -> int:
        """
        The highest of 30% of monthly adjusted income, 10% of monthly (countable)
        gross income, and the $50 minimum rent, rounded to the nearest dollar
        **half-up** per the Form HUD-50058 instructions (24 CFR 5.628(a)).

        Each prong is computed from the annual figure — 30% of a monthly amount is
        the annual over 40, and 10% is the annual over 120 — so an exact half-dollar
        stays exact instead of landing a hair under it, and rounding happens once,
        at the end. Implemented with ``Decimal`` and ``ROUND_HALF_UP``, following
        `KsHcv._total_tenant_payment`, not Python's built-in ``round()`` (banker's
        rounding).
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
        The household's reported rent stands in for the assisted unit's gross
        rent, falling back to the payment standard when no rent is reported.
        ``mortgage`` is deliberately excluded, matching `IlHcv` and `KsHcv` rather
        than `TxHcv`/`WaHcv`: gross rent is rent to owner plus the utility
        allowance (24 CFR 982.4), and an owner's mortgage payment is not a proxy
        for the rent of a future tenant-based voucher unit.
        """
        reported_rent = self.screen.calc_expenses("monthly", ["rent"])
        return reported_rent if reported_rent > 0 else float(payment_standard)

    def household_eligible(self, e: Eligibility):
        # Criterion 2: the household is a "family", which HUD's open-ended
        # definition reduces to household_size >= 1 — true of every screen the
        # frontend can submit, so this is unfalsifiable and kept simple on purpose.
        e.condition(self.screen.household_size is None or self.screen.household_size >= 1)

        # Criterion 4 (Missouri-specific, not sourced in federal HCV rule): a
        # household already holding Section 8 is not shown eligible for it again.
        e.condition(
            not self.screen.has_base_benefit("section_8"),
            messages.must_not_have_benefit("a Housing Choice Voucher"),
        )

        # Criterion 1: annual income at or below HUD's Very Low Income limit (50%
        # AMI) for the household's own county and size. A HUD lookup failure must
        # never raise out of the calculator and break the whole eligibility run.
        try:
            annual_income = int(self._annual_income())

            if self.screen.household_size is None:
                # No size means no limit to compare against. Passed inclusively
                # rather than compared — normally unreachable, since a null
                # household_size is a missing dependency and the program is not
                # calculated at all.
                return

            income_limit = hud_client.get_screen_il_ami(self.screen, self.ami_percent, self._year_period())
            e.condition(annual_income <= income_limit, messages.income(annual_income, income_limit))
        except HudIncomeClientError:
            # Expected when HUD data is unavailable (API down, county not found,
            # size outside 1-8, year unconfigured) — not eligible, without noise.
            e.condition(False, messages.income_limit_unknown())
        except Exception:
            # Unexpected failure — still degrade to not eligible rather than raise,
            # so one program cannot 500 the whole eligibility response, and log it.
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

            # 24 CFR 982.505(b): the payment is the lower of the two arms, less the
            # tenant payment.
            hap = max(0.0, min(float(payment_standard), gross_rent) - ttp)

            # Floored at $1, not $0: a household whose rent sits below its own
            # tenant payment is genuinely eligible but nets no subsidy, and the
            # frontend drops any program whose value is not greater than zero.
            return max(1, int(hap * 12))
        except HudIncomeClientError:
            # Expected when HUD data is unavailable — degrade to $0 without noise.
            # This is a value we could not compute rather than one that came out
            # at zero, so it is not floored: hiding the program is the honest
            # outcome.
            return 0
        except Exception:
            # Unexpected bug in the value calculation — still degrade to $0 so one
            # program cannot 500 the whole eligibility response, but log it.
            logger.exception(
                "MoHcv.household_value failed unexpectedly (white_label=%s, household_size=%s)",
                getattr(self.screen.white_label, "code", None),
                self.screen.household_size,
            )
            return 0
