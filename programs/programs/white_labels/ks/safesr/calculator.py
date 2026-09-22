from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages


class KsSafesr(ProgramCalculator):
    """
    Kansas Property Tax Relief for Low Income Seniors — SAFESR (Form K-40PT).

    A refund of 75% of the general property tax a low-income senior homeowner
    paid on their Kansas homestead. Flat 75%: no cap, no sliding scale, no
    minimum-refund floor.

    Eligibility (K.S.A. 79-32,263; 2025 K-40PT and Homestead booklet):
      - The claimant was 65 for the *entire* claim year — born on or before
        (claim year - 66). A current-age snapshot would wrongly admit someone
        who turned 65 mid-year, so this reads birth_year.
      - Household income (SAFESR definition, below) <= the published ceiling
        for the claim year ($25,380 for 2025).
      - Owns and occupies the homestead — proxied by housing expenses: a rent
        expense means renter (ineligible); anything else is treated as an owner.

    SAFESR household income is neither gross income nor K-40H's adjusted
    income. Do not reuse KsK40h's logic:
      - All four Social Security streams — sSRetirement, sSSurvivor, sSI,
        sSDependent — count at 100%. K-40H counts the first three at 50%, which
        would under-count SAFESR income by roughly half.
      - Excluded entirely: sSDisability, childSupport, gifts (the form's
        Excluded Income types the screener can identify) and the whole veteran
        bucket (see below).
      - A member who was not 18 for the whole claim year is skipped, keyed to
        birth year alone. K-40H keys its minor guard to `relationship`, which
        misses a 16-year-old grandChild or sibling, and to `age`, which the
        serializer back-fills at creation time and so reads the filing year
        during the Jan-Apr claim window.
      - Everyone else's income counts, including an adult child who is neither
        the claimant nor the spouse.

    Data gaps, and the direction each one errs (spec criteria 5-12):
      - The `veteran` bucket is excluded wholesale. This is a stand-in for a
        split the screener cannot make, NOT the Kansas rule: Kansas excludes
        veterans' *disability compensation* only and counts veterans' pensions
        and annuities in full, but the screener has a single "Veteran's Pension
        or Benefits" type. Widens results — a pension recipient near the
        ceiling may be admitted. Counting the bucket instead would wrongly deny
        a disabled veteran, and income only gates SAFESR, it never sizes the
        refund.
      - sSI and sSDependent count at 100% even though the disability share of
        each is excluded by the form; the screener has one type for each and
        cannot split them. Narrows results near the ceiling.
      - Social Security that converted from disability at full retirement age
        is excluded by the form but reports as sSRetirement, indistinguishable
        from an ordinary retiree's. Counted at 100%. Narrows results.
      - Federal EITC received, and grants and scholarships, are household
        income the screener does not collect. Omitted. Widens results.
      - A minor child's income counts only if that child holds title to the
        homestead — unobservable, so no minor is ever treated as a title
        holder. Widens results.
      - birth_year is None when birth_year_month is unset, and such a member
        silently fails the age test. "age" is the only dependency token
        covering birth data and does not guarantee birth_year_month is set.
      - Assumed met, because the screener cannot see them: the $350,000
        appraised-value cap, ownership for the whole period claimed, and
        whether a K-40H or K-40SVR claim was already filed for the year (only
        one of the three refunds may be claimed). All three are surfaced in the
        program description instead. No selection logic is built between the
        three refunds — both cards may surface and the description states the
        one-claim rule.

    Only one claimant per household per year (K.S.A. 79-4507), so the result is
    household-level: a two-senior household produces one refund, not two.

    Simplifications that change what the claimant receives rather than the
    computed refund: a Form ELG advancement and any debtor set-off are
    subtracted from the real refund and ignored here; where the homestead is
    co-owned with someone outside the household only that household's ownership
    share is claimable, and the screener captures no share; and the reported
    propertyTax expense may include special assessments, which line 11 excludes.
    All over-state the refund slightly.
    """

    program_code = "ks_safesr"

    # The published K-40PT ceiling, keyed by claim year. Statutorily 120% of the
    # two-person federal poverty level, but KDOR's published figures have not
    # always equalled the formula ($23,700 published against $23,664 derived for
    # 2023; $24,500 against $24,528 for 2024), so the published figure is
    # operative and the formula is only an annual cross-check.
    income_limit_by_year = {2025: 25_380}

    senior_age = 65
    adult_age = 18
    refund_percent = 0.75

    # Income types excluded from SAFESR household income. The first three are the
    # form's Excluded Income types the screener can identify; `veteran` is the
    # stand-in described in the class docstring, not a Kansas exclusion.
    excluded_types = ("sSDisability", "childSupport", "gifts", "veteran")

    # Median real estate tax on Kansas owner-occupied units NOT mortgaged
    # (U.S. Census ACS 5-year 2020-2024, table B25103). An MFB-owned estimate,
    # not a program-stated amount: the not-mortgaged cohort is the deliberate
    # choice because outright ownership correlates with the 65+ population
    # SAFESR screens, and it runs 23% below the mortgaged row ($3,056). It does
    # not reflect the income ceiling, so it sits above what the lowest-income
    # claimants pay — generous, never restrictive, and bypassed entirely by any
    # household that enters a real propertyTax expense.
    fallback_property_tax = 2_342

    dependencies = ("age", "income_type", "income_amount", "income_frequency", "expenses")

    def household_eligible(self, e: Eligibility):
        # Ownership proxy: a rent expense means renter, so ineligible; a mortgage,
        # a property tax row, or nothing entered is treated as an owner, since
        # paid-off homes are common among the 65+ population SAFESR serves. A
        # manufactured homeowner renting the lot is a known false negative.
        # has_expense matches on expense *type* and ignores the amount, which is
        # what this check wants — unlike the value fork below.
        e.condition(not self.screen.has_expense(["rent"]), messages.is_home_owner())

        income = self._household_income()
        income_limit = self.income_limit_by_year[self._claim_year()]
        e.condition(income <= income_limit, messages.income(income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        # The age test applies to the claimant only, but the framework requires at
        # least one eligible member, so it is evaluated per member and the
        # household rules are left to household_eligible. Only one claimant per
        # household may file, so the refund itself stays household-level.
        member = e.member
        claim_year = self._claim_year()

        # 65 for the *entire* claim year: born on or before (claim_year - 66).
        # birth_year is None when birth_year_month is unset, and such a member
        # fails here.
        e.condition(member.birth_year is not None and member.birth_year <= claim_year - (self.senior_age + 1))

    def _claim_year(self) -> int:
        """
        The tax year the age gate and the income ceiling both describe.

        Program.year is a foreign key to a FederalPoveryLimit row, and
        import_program_config only logs a warning when no row matches, so a
        mis-seeded config imports and leaves it None. Falling back to the newest
        year in the ceiling table — rather than to a literal — keeps the two
        rules describing the same year, which a hardcoded year in either place
        would not. A configured year with no ceiling published for it takes the
        same fallback for the same reason.
        """
        latest = max(self.income_limit_by_year)

        if self.program.year is None:
            return latest

        year = int(self.program.year.period)

        return year if year in self.income_limit_by_year else latest

    def _household_income(self) -> int:
        """SAFESR household income (see the class docstring)."""
        claim_year = self._claim_year()
        total = 0.0

        for member in self.screen.household_members.all():
            # Skip anyone who was not 18 for the whole claim year. Keyed to birth
            # year alone: relationship misses a minor grandchild or sibling, and
            # `age` carries the filing year during the Jan-Apr claim window. A
            # member with no birth year is treated as an adult, which counts their
            # income — the conservative direction for a gate.
            if member.birth_year is not None and member.birth_year >= claim_year - self.adult_age:
                continue

            total += member.calc_gross_income("yearly", ["all"], exclude=list(self.excluded_types))

        return int(total)

    def household_value(self) -> int:
        property_tax = self.screen.calc_expenses("yearly", ["propertyTax"])

        # The fork is the summed amount, not has_expense: the expense form permits
        # a propertyTax row entered at $0, and gating on the type would hand an
        # eligible household a $0 refund that the results page renders as $0/year.
        if property_tax <= 0:
            property_tax = self.fallback_property_tax

        # KDOR works in whole dollars — every money line on the K-40PT has a fixed
        # `00` cents box.
        return round(self.refund_percent * property_tax)
