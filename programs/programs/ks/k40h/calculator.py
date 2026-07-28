from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
import programs.programs.messages as messages


class KsK40h(ProgramCalculator):
    """
    Kansas Homestead Property Tax Refund (K-40H).

    A refund of a portion of the general property tax paid on a low-income
    homeowner's primary residence. Renters are NOT eligible (the pre-2013
    15%-of-rent provision was repealed).

    Eligibility (K.S.A. 79-4501 et seq.; 2025 K-40H booklet):
      - At least one categorical path is met:
          (a) born on/before the claim year - 56 (age 55+ the entire year)
          (b) blind / totally & permanently disabled
          (c) has a dependent child who is under 18 the entire claim year
          (d/e) disabled veteran / surviving spouse — proxied by a veteran
                income stream
      - Household income (K-40H definition, see below) <= $43,389 (2025 claim year)
      - Owns and occupies the homestead — proxied by housing expenses:
          rent > 0 -> ineligible; else mortgage/propertyTax > 0 or nothing -> owner

    Household income is NOT gross income. Adjustments (2025 booklet Line 10):
      - count only 50% of SS retirement/survivor and non-disability SSI
        (sSRetirement, sSSurvivor, sSI)
      - exclude entirely: SS disability (sSDisability), child support, gifts
      - the sSI stream can't distinguish aged/blind (50%) from disability (0%);
        default to 50% per the booklet's general rule (conservative)

    Benefit value = allowed property tax x refund percentage:
      - allowed property tax = min(annual propertyTax expense, $700); if no
        propertyTax expense entered, assume the $700 cap
      - refund percentage from the income-based table (100% at <=$6,000 down to
        5% at $26,001-$43,389)
      - refunds under $5 are not issued (return 0)

    Data gaps handled as inclusivity assumptions (see spec.md): $350k home-value
    cap, dependent-status, full-year residency/occupancy, disability
    certification/SGA, VA 50%+ rating, and the statute-only anti-abuse bars — all
    verified at application, not by the screener.
    """

    income_limit = 43_389
    max_property_tax = 700
    min_refund = 5
    senior_age = 55

    # Income types counted at 50% (SS retirement/survivor, non-disability SSI).
    half_count_types = ("sSRetirement", "sSSurvivor", "sSI")
    # Income types excluded entirely from K-40H household income.
    excluded_types = ("sSDisability", "childSupport", "gifts")

    # 2025 refund-percentage table: (income upper bound inclusive, percent).
    refund_table = [
        (6_000, 1.00),
        (7_000, 0.96),
        (8_000, 0.92),
        (9_000, 0.88),
        (10_000, 0.84),
        (11_000, 0.80),
        (12_000, 0.76),
        (13_000, 0.72),
        (14_000, 0.68),
        (15_000, 0.64),
        (16_000, 0.60),
        (17_000, 0.55),
        (18_000, 0.50),
        (19_000, 0.45),
        (20_000, 0.40),
        (21_000, 0.35),
        (22_000, 0.30),
        (23_000, 0.25),
        (24_000, 0.20),
        (25_000, 0.15),
        (26_000, 0.10),
        (43_389, 0.05),
    ]

    dependencies = [
        "age",
        "income_type",
        "income_amount",
        "income_frequency",
        "expenses",
        "household_size",
        "relationship",
    ]

    def household_eligible(self, e: Eligibility):
        # Ownership proxy: renters are ineligible; mortgage/propertyTax or nothing
        # entered is treated as a homeowner (paid-off homes are common in the 55+
        # target demographic). A lot-renting manufactured homeowner is a known
        # false-negative edge case (spec criterion 4).
        e.condition(not self.screen.has_expense(["rent"]), messages.is_home_owner())

        # Household income (K-40H adjusted) must not exceed the limit.
        income = self._household_income()
        e.condition(income <= self.income_limit, messages.income(income, self.income_limit))

        # Refunds under $5 are not issued (KDOR). A computed refund below the floor
        # means the household is not eligible for a payable benefit — fail eligibility
        # rather than showing an eligible $0 result. (Also covers the no-property-tax
        # / fully-tax-exempt case, which naturally yields a $0 refund.)
        e.condition(self._refund_amount() >= self.min_refund)

    def member_eligible(self, e: MemberEligibility):
        # At least one member must satisfy a categorical path. Eligibility is
        # household-level, but the framework requires >=1 eligible member, so we
        # evaluate the categorical test per member and let household_eligible
        # gate the income/ownership rules.
        member = e.member
        e.condition(self._meets_categorical(member))

    def _meets_categorical(self, member) -> bool:
        claim_year = int(self.program.year.period) if self.program.year else 2025

        # (a) Age 55+ the entire claim year -> born on/before (claim_year - 56).
        # Use birth_year (not the current-snapshot age) per spec criterion 1(a).
        if member.birth_year is not None and member.birth_year <= claim_year - (self.senior_age + 1):
            return True

        # (b) Blind or totally & permanently disabled.
        if member.visually_impaired or member.disabled or member.long_term_disability:
            return True

        # (d/e) Disabled veteran / surviving spouse — proxied by a veteran income
        # stream on any member (checked at household level below via the head; here
        # per-member so a veteran member satisfies it).
        if member.calc_gross_income("yearly", ["veteran"]) > 0:
            return True

        # (c) Has a dependent child under 18 the entire claim year. This is a
        # household property of the claimant, so check whether ANY child member
        # qualifies by birth year.
        for child in self.screen.household_members.all():
            if child.relationship not in ("child", "stepChild", "fosterChild", "grandChild"):
                continue
            if child.birth_year is None:
                continue
            # under 18 the entire year: born on/after (claim_year - 17), and born
            # before the claim year.
            if claim_year - 17 <= child.birth_year < claim_year:
                return True

        return False

    def _household_income(self) -> int:
        """K-40H adjusted household income (see class docstring)."""
        total = 0.0
        for member in self.screen.household_members.all():
            # Dependent minors/incapacitated members without title are excluded;
            # approximate as: exclude dependent children's income (spec criterion 2).
            if member.relationship in ("child", "stepChild", "fosterChild") and (member.age is None or member.age < 18):
                continue

            # Everything except the excluded and half-counted types, at full value.
            full = member.calc_gross_income(
                "yearly", ["all"], exclude=list(self.excluded_types) + list(self.half_count_types)
            )
            total += full

            # SS retirement/survivor + non-disability SSI counted at 50%.
            half = member.calc_gross_income("yearly", list(self.half_count_types))
            total += 0.5 * half

        return int(total)

    def _refund_amount(self) -> float:
        """
        Exact (unrounded) K-40H refund = allowed property tax x refund-table %.
        Used both to gate eligibility (>= $5 floor) and to produce the value.
        """
        income = self._household_income()

        percent = 0.0
        for upper, pct in self.refund_table:
            if income <= upper:
                percent = pct
                break

        if percent == 0.0:
            return 0.0

        # Allowed property tax: min(annual propertyTax expense, $700); if none
        # entered, assume the $700 cap (median KS residential bills exceed $700).
        property_tax = self.screen.calc_expenses("yearly", ["propertyTax"])
        allowed = min(property_tax, self.max_property_tax) if property_tax > 0 else self.max_property_tax

        return allowed * percent

    def household_value(self) -> int:
        refund = self._refund_amount()

        # Refunds under $5 are not issued (the floor is enforced as an eligibility
        # condition in household_eligible; return 0 here as a defensive fallback).
        if refund < self.min_refund:
            return 0

        return round(refund)
