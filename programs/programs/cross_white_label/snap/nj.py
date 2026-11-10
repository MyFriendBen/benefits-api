"""NJ SNAP."""

from decimal import ROUND_HALF_UP, Decimal

from programs.programs.cross_white_label.snap.mfb_base import MfbSnap, _by_size

# 185% of poverty, monthly: the gross income standard for broad-based categorical eligibility,
# 2026-10-01 through 2027-09-30 (N.J.A.C. 10:87-2.36(a)).
BBCE_GROSS_LIMITS = {1: 2_461, 2: 3_337, 3: 4_212, 4: 5_088, 5: 5_964, 6: 6_839, 7: 7_715, 8: 8_591}
BBCE_GROSS_LIMIT_PER_ADDITIONAL = 876

# New Jersey's heating and cooling standard utility allowance, monthly, effective 2025-10-01. The
# amount effective 2026-10-01 is not published.
HEATING_COOLING_ALLOWANCE = 977
# N.J.S.A. 44:10-111: a household with a federal allotment of at least 1 dollar and under this gets
# a State supplement up to it.
STATE_MINIMUM_BENEFIT = 95


def bbce_gross_limit(household_size: int) -> int:
    """Monthly gross income a household must be under to qualify through NJ's 185% route."""
    return _by_size(BBCE_GROSS_LIMITS, BBCE_GROSS_LIMIT_PER_ADDITIONAL, household_size)


class NjSnap(MfbSnap):
    """
    New Jersey SNAP (NJ SNAP, N.J.A.C. 10:87). Inherits the federal shape from ``MfbSnap``; NJ
    changes five things:

    - a household whose gross income, less child support paid, is under 185% of poverty is
      categorically eligible, with no net income test and no resource test. The test is "less
      than": income at the limit does not qualify. Like the federal categorical route, it still
      needs an allotment above zero for a household of three or more
    - utilities are one standard allowance, not actual bills: 977 dollars for a household reporting
      a ``heating`` or ``cooling`` expense; any other household's reported ``telephone`` and
      ``otherUtilities`` stand in for NJ's unpublished limited and telephone allowances
    - each income amount and the earned income, dependent care, medical and shelter deductions are
      rounded to the nearest dollar, half up (N.J.A.C. 10:87-6.16(c))
    - the 30% of net income is rounded up to the next dollar, as the federal base does
    - a federal allotment from 1 to 94 dollars is raised to 95 by the State supplement (N.J.S.A.
      44:10-111). A household entitled to no federal benefit gets nothing

    NJ's drug felony exemption (everyone domiciled in the state) removes a barrier the calculator
    never checks, so it needs no code; the program record's description says so.

    Approximations beyond the base's, all from the spec's data gaps: a household reporting
    ``heating`` or ``cooling`` gets the allowance even when it pays them within its rent, and an
    elderly or disabled household with a LIHEAP benefit but no heating or cooling bill uses its
    reported bills; the 185% income is not reduced by the exclusions every SNAP household gets,
    other than child support paid; the allowance is assumed to still be 977 dollars.

    The value is the monthly allotment made annual. It is a full month, with the State supplement
    included.

    The spec is ``programs/cross_white_label/snap/nj/snap_nj_spec.md`` in program-ops.
    """

    program_code = "nj_snap"

    def categorically_eligible(self) -> bool:
        return super().categorically_eligible() or self.under_bbce_limit()

    def under_bbce_limit(self) -> bool:
        """Gross income less child support paid is below 185% of poverty."""
        return self.countable_income < bbce_gross_limit(self.household_size)

    def utility_costs(self) -> Decimal:
        if self.screen.has_expense(["heating", "cooling"]):
            return Decimal(HEATING_COOLING_ALLOWANCE)

        return self.expenses(["telephone", "otherUtilities"])

    def round_amount(self, amount: Decimal) -> Decimal:
        return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    def state_allotment(self, federal_allotment: int) -> int:
        if 1 <= federal_allotment < STATE_MINIMUM_BENEFIT:
            return STATE_MINIMUM_BENEFIT

        return federal_allotment
