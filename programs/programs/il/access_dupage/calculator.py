from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator
import programs.programs.messages as messages


class IlAccessDuPage(ProgramCalculator):
    """
    Access DuPage (IL)

    Free or low-cost in-kind health care for uninsured adults in DuPage County, run by
    the DuPage Health Coalition. Access DuPage is not health insurance and provides no
    fixed dollar benefit, so the calculator determines eligibility only. It returns a
    nominal value of $1 per eligible member: the frontend hides any program whose value
    is not > 0 (filterPrograms.ts), so a literal $0 would never render. The "$1" is never
    shown to users — the program's estimated_value translation override displays "Varies"
    instead. This mirrors IlTransportationMixin.member_value.

    Eligibility (from spec.md):
      - Permanent DuPage County resident. The screener verifies county, not the 30-day
        residency/intent requirement, so that portion is a data gap -> default inclusive.
      - Household income at or below 250% of the Federal Poverty Level.
      - Not eligible for other health coverage -> at least one household member who
        reports being uninsured. Current Medicaid, Medicare, or employer coverage
        disqualifies that member. Eligibility (vs. enrollment) for Medicaid/ACA/employer
        plans is a data gap -> default inclusive for those who report being uninsured.
      - Age 19 or older. There is no upper age limit; people 65+ are effectively excluded
        via Medicare eligibility (criterion 3), not an age cutoff.
    """

    fpl_percent = 2.5
    min_age = 19
    # Nominal sentinel so the program clears the frontend's `value > 0` visibility
    # filter; the "Varies" estimated_value override is what users actually see.
    member_amount = 1
    eligible_counties = ["DuPage"]
    # Coverage that disqualifies a member from Access DuPage
    disqualifying_insurance = ["medicaid", "medicare", "employer", "private"]

    dependencies = [
        "age",
        "income_amount",
        "income_frequency",
        "household_size",
        "county",
        "health_insurance",
    ]

    def household_eligible(self, e: Eligibility):
        # Must be a DuPage County resident
        e.condition(self.screen.county in self.eligible_counties, messages.location())

        # Household income at or below 250% FPL
        gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
        e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Age 19 or older
        e.condition(member.age is not None and member.age >= self.min_age)

        # Must report being uninsured and not have disqualifying coverage
        e.condition(member.has_insurance_types(["none"]))
        e.condition(not member.has_insurance_types(self.disqualifying_insurance))
