from programs.framework.base import ProgramCalculator, Eligibility
import programs.framework.eligibility_messages as messages
from screener.models import HouseholdMember
from typing import ClassVar


class MoLiheap(ProgramCalculator):
    """MO LIHEAP (Energy Assistance) — a one-time payment toward home heating
    and cooling costs, administered by the Missouri Family Support Division.

    Eligibility (see specs/mo.md):
      * Criterion 1: countable monthly income at or below 60% of Missouri's State
        Median Income for the household size. Missouri elected the SMI standard,
        so this is a published dollar table rather than an FPL multiple. Countable
        income is gross income less two exclusions (a member under 18's earned
        income, and interest/dividend income) and four deductions (20% of earned
        income, $100 once where the applicant or spouse is 65+ or has a
        disability, child support paid out of the household, and the Medicare
        Part B premium per Medicare-covered member).
      * Criterion 2: the household must be responsible for its home energy costs.
        Missouri requires an account in a member's name or a qualifying
        renter/landlord arrangement; the screener has no such field, so this
        follows the ks_lieap / nc_lieap precedent and infers responsibility from a
        housing or utility expense. A household whose landlord bears the energy
        cost with no pass-through has rent but no responsibility and is shown as
        eligible.
      * Criterion 5: at least one member aged 15 or older. Missouri expects an
        applicant 18 or over but accepts a 15- to 17-year-old where the household
        has no adult, so under-15 is the only outright denial.

    Handled outside the calculator:
      * Criterion 3 (citizenship) — the program's `legal_status_required` config.
        Missouri disqualifies only on the *applicant's* status and merely drops
        other non-qualifying members from the household count, which the screener
        cannot reproduce (it collects no per-member status).
      * Criterion 4 (Missouri residency) — enforced at intake: the MO screener
        gates its ZIP step on `MoConfigurationData.counties_by_zipcode`, so a
        non-Missouri ZIP never reaches this calculator.

    Not modelled, per the spec's resolved implementation decisions:
      * The $3,000 resource limit. `Screen.household_assets` is not Missouri's
        countable figure in either direction, so applying it would exclude
        households Missouri accepts. Surfaced in the program description instead.
      * Primary heating fuel, which sets the real award, and the CARS recoupment
        that can reduce it — neither is collected.
      * The utilities-included renter payment (a share of annual rent). The
        screener records no utilities-included tenancy, and the sources conflict
        on its size. Those renters get the standard estimate below.

    Benefit value is a flat $153 lump sum — Missouri's published minimum Energy
    Assistance benefit, chosen as a deliberate conservative estimate because the
    per-fuel figures Missouri publishes are maximums and the matrix that sets the
    award within them is not.
    """

    program_code = "mo_liheap"

    #: One-time payment. `value_format: lump_sum` on the program row, so this is
    #: the award itself and not an annualized figure.
    amount = 153

    #: Monthly 60% SMI income limit by household size — MyDSS Benefit Program
    #: Income Limits, as of 04/01/2026. The live screener caps household size at
    #: 8, so rows 9 and 10 and the increment below are currently unreachable.
    income_limits: ClassVar[dict[int, int]] = {
        1: 2_840,
        2: 3_714,
        3: 4_588,
        4: 5_461,
        5: 6_335,
        6: 7_209,
        7: 7_373,
        8: 7_537,
        9: 7_701,
        10: 7_864,
    }
    #: Added to the size-10 limit for each member past 10.
    income_limit_increment = 164

    #: A housing or utility expense stands in for energy-cost responsibility.
    expenses = ("rent", "mortgage", "heating", "cooling", "otherUtilities")

    #: Missouri's earned-income definition, which includes roomer-boarder income.
    #: Drives both the 20% deduction and the under-18 exclusion.
    earned_income_types = ("wages", "selfEmployment", "boarder")
    #: Interest and dividend income, excluded outright. `deferredComp` is MFB's
    #: "Withdrawals from Deferred Compensation (IRA, Keogh, etc.)", which
    #: Missouri lists under the same exclusion.
    excluded_income_types = ("investment", "deferredComp")
    earned_income_deduction = 0.20
    #: Earned income of a member below this age is excluded; their SSA income
    #: still counts.
    minor_age = 18

    #: Granted once per household where the applicant or spouse is elderly or has
    #: a disability, never once per qualifying member.
    medical_deduction = 100
    medical_deduction_min_age = 65
    #: CMS standard 2026 Part B premium. Missouri deducts the member's actual
    #: premium and only where they pay it rather than being in buy-in; neither is
    #: screenable, so this over-deducts for buy-in households, which admits
    #: households rather than excluding them.
    medicare_premium = 202.90

    #: Missouri denies an application from an applicant under 15 outright.
    min_applicant_age = 15

    dependencies: ClassVar[list[str]] = [
        "income_frequency",
        "income_amount",
        "household_size",
    ]

    def household_eligible(self, e: Eligibility):
        # Criterion 5: someone old enough to be the applicant
        e.condition(self._has_eligible_applicant(), messages.older_than(self.min_applicant_age))

        # Criterion 2: responsible for home energy costs (directly or via rent)
        e.condition(self.screen.has_expense(self.expenses))

        # Criterion 1: countable monthly income at or below 60% SMI
        income = self._countable_income()
        income_limit = self._income_limit()
        e.condition(income <= income_limit, messages.income(income, income_limit))

    def _income_limit(self) -> int:
        """The size's row of Missouri's 60% SMI table, extended by
        `income_limit_increment` past the largest published row."""
        household_size = self.screen.household_size or 1
        largest_published = max(self.income_limits)

        if household_size >= largest_published:
            return (
                self.income_limits[largest_published]
                + (household_size - largest_published) * self.income_limit_increment
            )

        return self.income_limits.get(household_size, self.income_limits[1])

    def _countable_income(self) -> float:
        """Monthly gross income less Missouri's exclusions and deductions.

        Rounded to cents because the boundary cases turn on them: $3,551 of
        earned income is $2,840.80 after the 20% deduction and must fail a
        $2,840 limit, so truncating to whole dollars would wrongly admit it.
        """
        gross = 0.0
        earned = 0.0

        for member in self.screen.household_members.all():
            exclude = list(self.excluded_income_types)
            if self._is_minor(member):
                exclude += list(self.earned_income_types)
            else:
                earned += member.calc_gross_income("monthly", list(self.earned_income_types))
            gross += member.calc_gross_income("monthly", ["all"], exclude=exclude)

        deductions = earned * self.earned_income_deduction
        if self._medical_deduction_applies():
            deductions += self.medical_deduction
        deductions += self.screen.calc_expenses("monthly", ["childSupport"])
        deductions += self.medicare_premium * self._medicare_member_count()

        return round(max(0.0, gross - deductions), 2)

    def _is_minor(self, member: HouseholdMember) -> bool:
        """Whether `member`'s earned income is excluded. A member whose age is
        unknown counts as an adult: Missouri grants the exclusion on proof of
        age, so an unproven one is not assumed."""
        age = member.calc_age()
        return age is not None and age < self.minor_age

    def _medical_deduction_applies(self) -> bool:
        """Whether the $100 medical deduction is due. Missouri tests the
        applicant and spouse only — a qualifying parent or child does not earn it
        — and allows it once even when both qualify."""
        for member in self.screen.household_members.all():
            if not (member.is_head() or member.is_spouse()):
                continue

            age = member.calc_age()
            if age is not None and age >= self.medical_deduction_min_age:
                return True
            if member.has_disability():
                return True

        return False

    def _medicare_member_count(self) -> int:
        return sum(1 for member in self.screen.household_members.all() if member.has_insurance("medicare"))

    def _has_eligible_applicant(self) -> bool:
        for member in self.screen.household_members.all():
            age = member.calc_age()
            if age is not None and age >= self.min_applicant_age:
                return True

        return False
