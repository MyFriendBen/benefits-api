from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property

from programs.framework.base import Eligibility, ProgramCalculator
from programs.programs.white_labels.nj.income_tax import (
    EXCLUDED_INCOME_TYPES,
    TABLE_A,
    TABLE_B,
    filers,
    income_tax,
)
from screener.models import HouseholdMember


class NjPropertyTaxDeductionCredit(ProgramCalculator):
    """
    New Jersey Property Tax Deduction/Credit: homeowners and renters claim, on the NJ-1040, a
    deduction for the property tax they paid (18% of rent for a renter, capped at 15,000) or a
    refundable 50 dollar credit, whichever saves more. Judged over the program's tax year.
    Rules and figures: program-ops
    `programs/white_labels/nj/property_tax_deduction_credit/nj_property_tax_deduction_credit_spec.md`.

    Two routes, both needing rent or property tax:

    - Filer: NJ gross income above the filing threshold (20,000 with a spouse or a dependent,
      10,000 otherwise). The value is the deduction's tax saving or the credit, whichever is
      larger.
    - Senior or disabled non-filer: income at or below the threshold, and the head or spouse
      65 or older at the end of the tax year, or blind or disabled. The value is the credit.

    NJ gross income is the head's and spouse's income less the types New Jersey doesn't tax and
    the pension exclusion. Taxable income subtracts the exemptions and the medical deduction.
    Tax is priced from the Tax Table below 100,000 and the rate schedules above it. The saving
    is rounded half up to the dollar.

    Data gaps (spec §5): whether the home is subject to property tax, its unit count and
    facilities, which property an expense is for, NJ's full gross income definition, filing
    status, and the total-and-permanent disability standard. Approximations (spec §7): taxable
    income takes only the exemptions and the medical deduction, and the value ignores
    married-filing-separately halving, part-year proration, ownership and rent shares, Senior
    Freeze base years, veterans' discharge status and head-of-household status.
    """

    program_code = "nj_property_tax_deduction_credit"

    filing_threshold_joint = 20_000
    filing_threshold_single = 10_000

    credit_amount = 50
    deduction_cap = Decimal(15_000)
    rent_as_property_tax = Decimal("0.18")

    personal_exemption = 1_000
    senior_exemption = 1_000
    senior_age = 65
    blind_disabled_exemption = 1_000
    veteran_exemption = 6_000
    dependent_exemption = 1_500
    medical_floor = Decimal("0.02")

    pension_exclusion_age = 62
    pension_exclusion_cap_joint = Decimal(100_000)
    pension_exclusion_cap_single = Decimal(75_000)
    full_pension_exclusion_limit = 100_000
    # Each band: the income it runs to, and the share of the pension excluded (joint, not joint).
    partial_pension_exclusion_bands = (
        (125_000, Decimal("0.5"), Decimal("0.375")),
        (150_000, Decimal("0.25"), Decimal("0.1875")),
    )

    dependencies = [
        "age",
        "relationship",
        "student",
        "visually_impaired",
        "disabled",
        "long_term_disability",
        "income_type",
        "income_amount",
        "income_frequency",
        "expense_type",
        "expense_amount",
        "expense_frequency",
    ]

    def household_eligible(self, e: Eligibility) -> None:
        e.condition(self._property_tax_paid > 0 or self._rent_paid > 0)

        if not self._above_filing_threshold:
            e.condition(any(self._is_senior(m) or m.has_disability() for m in self._filers))

    def household_value(self) -> int:
        if not self._above_filing_threshold:
            return self.credit_amount

        saving = self._deduction_saving.quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return max(int(saving), self.credit_amount)

    @cached_property
    def _filers(self) -> list[HouseholdMember]:
        return filers(self.screen)

    @cached_property
    def _is_joint(self) -> bool:
        return self.screen.is_joint()

    @cached_property
    def _dependent_count(self) -> int:
        return sum(1 for m in self.screen.household_members.all() if m.is_dependent())

    @cached_property
    def _property_tax_paid(self) -> Decimal:
        return Decimal(str(self.screen.calc_expenses("yearly", ["propertyTax"])))

    @cached_property
    def _rent_paid(self) -> Decimal:
        return Decimal(str(self.screen.calc_expenses("yearly", ["rent"])))

    @cached_property
    def _counted_income(self) -> Decimal:
        """The filers' income before the pension exclusion (S in the spec)."""
        return sum(
            (
                Decimal(str(m.calc_gross_income("yearly", ["all"], exclude=list(EXCLUDED_INCOME_TYPES))))
                for m in self._filers
            ),
            Decimal(0),
        )

    @cached_property
    def _pension_exclusion(self) -> Decimal:
        """The pension of filers 62 or older or disabled that New Jersey excludes (P in the spec)."""
        pension = sum(
            (
                Decimal(str(m.calc_gross_income("yearly", ["pension"])))
                for m in self._filers
                if self._age_at_year_end(m) >= self.pension_exclusion_age or m.has_disability()
            ),
            Decimal(0),
        )
        income = self._counted_income

        if income <= self.full_pension_exclusion_limit:
            cap = self.pension_exclusion_cap_joint if self._is_joint else self.pension_exclusion_cap_single
            return min(pension, cap)

        for band_top, joint_share, single_share in self.partial_pension_exclusion_bands:
            if income <= band_top:
                return pension * (joint_share if self._is_joint else single_share)

        return Decimal(0)

    @cached_property
    def _gross_income(self) -> Decimal:
        """New Jersey gross income (G in the spec)."""
        return self._counted_income - self._pension_exclusion

    @cached_property
    def _above_filing_threshold(self) -> bool:
        if self._is_joint or self._dependent_count > 0:
            threshold = self.filing_threshold_joint
        else:
            threshold = self.filing_threshold_single

        return self._gross_income > threshold

    @cached_property
    def _exemptions(self) -> int:
        """E in the spec. The senior, disability and veteran exemptions are the filers' alone."""
        domestic_partners = sum(1 for m in self.screen.household_members.all() if m.relationship == "domesticPartner")
        claimants = self._filers

        return (
            self.personal_exemption * (1 + int(self._is_joint) + domestic_partners)
            + self.senior_exemption * sum(1 for m in claimants if self._is_senior(m))
            + self.blind_disabled_exemption * sum(1 for m in claimants if m.has_disability())
            + self.veteran_exemption * sum(1 for m in claimants if m.veteran is True)
            + self.dependent_exemption * self._dependent_count
        )

    @cached_property
    def _taxable_income(self) -> Decimal:
        """TI in the spec: gross income less the exemptions and the medical deduction."""
        income = self._gross_income
        medical = Decimal(str(self.screen.calc_expenses("yearly", ["medical"])))
        medical_deduction = max(Decimal(0), medical - self.medical_floor * income)

        return max(Decimal(0), income - self._exemptions - medical_deduction)

    @cached_property
    def _deduction_saving(self) -> Decimal:
        """The tax the deduction saves: tax before it less tax after it."""
        deduction = min(self._property_tax_paid + self.rent_as_property_tax * self._rent_paid, self.deduction_cap)
        table = TABLE_B if self._is_joint or self._dependent_count > 0 else TABLE_A
        income = self._taxable_income

        return income_tax(income, table) - income_tax(max(Decimal(0), income - deduction), table)

    def _age_at_year_end(self, member: HouseholdMember) -> int:
        age = member.age_at_end_of_year(self.tax_year)
        return age if age is not None else 0

    def _is_senior(self, member: HouseholdMember) -> bool:
        return self._age_at_year_end(member) >= self.senior_age
