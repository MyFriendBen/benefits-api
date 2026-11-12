from decimal import ROUND_HALF_UP, Decimal
from functools import cached_property

import programs.framework.eligibility_messages as messages
from programs.framework.base import Eligibility
from programs.programs.white_labels.federal.cdcc.calculator import FederalCdcc
from programs.programs.white_labels.nj.income_tax import EXCLUDED_INCOME_TYPES, filers
from screener.models import HouseholdMember


class NjCdcc(FederalCdcc):
    """
    New Jersey Child and Dependent Care Credit, claimed on line 64 of the NJ-1040 for the
    program's tax year: a percentage of the federal credit, set by New Jersey taxable income,
    for households with New Jersey taxable income of 150,000 or less. Refundable.
    Rules and figures: program-ops `programs/white_labels/nj/cdcc/nj_cdcc_spec.md`.

    The federal credit is worked out by ``FederalCdcc``, so both programs read the same rules,
    and New Jersey requires it to be above 0. New Jersey taxable income is the head's and a
    spouse's income less New Jersey's exempt types, less the exemptions (personal, 65 or older,
    blind or disabled, dependents, college-dependents), medical costs over 2% of that income and,
    above the filing threshold, the property tax deduction (property tax plus 18% of rent, capped
    at 15,000). The credit is rounded once, half up, with no minimum: a household whose credit
    rounds to 0 is eligible at 0.

    Data gaps and approximations (spec §4, §5 and §7): residency in the tax year and part-year
    proration; filing status, civil unions and the separate return of whoever claims the credit;
    the pension, other retirement income and special exclusions; the veteran and domestic partner
    exemptions; other deductions; the conditions on the college, blind or disabled, medical and
    property tax rules; whether the deduction beats the Property Tax Credit; military pay; and
    refund offsets for debts. The federal credit carries its own spec's approximations.
    """

    program_code = "nj_cdcc"

    income_limit = 150_000
    # Spec §7: the share of the federal credit by the top of each taxable-income band.
    nj_rates = (
        (30_000, Decimal("0.50")),
        (60_000, Decimal("0.40")),
        (90_000, Decimal("0.30")),
        (120_000, Decimal("0.20")),
        (150_000, Decimal("0.10")),
    )

    # Spec §4 `nj_taxable_income_limit`: exemptions, deductions and their limits.
    personal_exemption = 1_000
    senior_exemption = 1_000
    senior_age = 65
    blind_disabled_exemption = 1_000
    dependent_exemption = 1_500
    college_exemption = 1_000
    college_age_limit = 22
    medical_floor = Decimal("0.02")
    rent_as_property_tax = Decimal("0.18")
    deduction_cap = Decimal(15_000)
    filing_threshold_joint = 20_000
    filing_threshold_single = 10_000

    dependencies = FederalCdcc.dependencies + [
        "student",
        "visually_impaired",
        "disabled",
        "long_term_disability",
    ]

    def household_eligible(self, e: Eligibility) -> None:
        super().household_eligible(e)
        # Spec §4 `federal_cdcc_allowed`: the federal credit above 0. Checked only once the
        # federal rules pass, since the credit needs a filer to compute.
        if e.eligible:
            e.condition(self._federal_credit > 0)

        # Spec §4 `nj_taxable_income_limit`
        income = self._taxable_income
        e.condition(income <= self.income_limit, messages.income(income, self.income_limit))

    def household_value(self) -> int:
        """Spec §7: the band's share of the federal credit, rounded once, with no minimum."""
        credit = self._nj_rate * self._federal_credit
        return int(credit.quantize(Decimal(1), rounding=ROUND_HALF_UP))

    @cached_property
    def _federal_credit(self) -> int:
        return FederalCdcc.household_value(self)

    @property
    def _nj_rate(self) -> Decimal:
        for top, rate in self.nj_rates:
            if self._taxable_income <= top:
                return rate

        return Decimal(0)

    @cached_property
    def _nj_filers(self) -> list[HouseholdMember]:
        """The head and a `spouse` member; a domestic partner files their own return."""
        return filers(self.screen)

    @cached_property
    def _dependents(self) -> list[HouseholdMember]:
        """Members who are dependents in the tax year, judged by their age at its end."""
        return [m for m in self.screen.household_members.all() if m.is_dependent(self.tax_year)]

    @cached_property
    def _gross_income(self) -> Decimal:
        """The filers' income less the types New Jersey doesn't tax."""
        return sum(
            (
                Decimal(str(m.calc_gross_income("yearly", ["all"], exclude=list(EXCLUDED_INCOME_TYPES))))
                for m in self._nj_filers
            ),
            Decimal(0),
        )

    @cached_property
    def _exemptions(self) -> int:
        filers = self._nj_filers
        dependents = self._dependents
        return (
            self.personal_exemption * len(filers)
            + self.senior_exemption * sum(1 for m in filers if self._is_senior(m))
            + self.blind_disabled_exemption * sum(1 for m in filers if m.has_disability())
            + self.dependent_exemption * len(dependents)
            + self.college_exemption * sum(1 for m in dependents if self._is_college_dependent(m))
        )

    @cached_property
    def _medical_deduction(self) -> Decimal:
        medical = Decimal(str(self.screen.calc_expenses("yearly", ["medical"])))
        return max(Decimal(0), medical - self.medical_floor * self._gross_income)

    @cached_property
    def _property_tax_deduction(self) -> Decimal:
        """Property tax plus 18% of rent, capped, taken only above the filing threshold."""
        if self.screen.is_joint() or self._dependents:
            threshold = self.filing_threshold_joint
        else:
            threshold = self.filing_threshold_single

        if self._gross_income <= threshold:
            return Decimal(0)

        property_tax = Decimal(str(self.screen.calc_expenses("yearly", ["propertyTax"])))
        rent = Decimal(str(self.screen.calc_expenses("yearly", ["rent"])))
        return min(property_tax + self.rent_as_property_tax * rent, self.deduction_cap)

    @cached_property
    def _taxable_income(self) -> Decimal:
        income = self._gross_income - self._exemptions - self._medical_deduction - self._property_tax_deduction
        return max(Decimal(0), income)

    def _is_senior(self, member: HouseholdMember) -> bool:
        age = member.age_at_end_of_year(self.tax_year)
        return age is not None and age >= self.senior_age

    def _is_college_dependent(self, member: HouseholdMember) -> bool:
        age = member.age_at_end_of_year(self.tax_year)
        return bool(member.student_full_time) and age is not None and age < self.college_age_limit
