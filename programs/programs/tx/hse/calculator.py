from programs.programs.calc import ProgramCalculator, Eligibility
from typing import ClassVar


class TxHse(ProgramCalculator):
    """
    Texas Homestead Exemption (HSE)

    Reduces the appraised value of a homeowner's primary residence for property
    tax purposes. All Texas homeowners who occupy their home as their principal
    residence are eligible.

    Eligibility:
    - Applicant must own and occupy the property as their principal residence
      (proxied here by the presence of a mortgage expense).
    - Texas residency is handled automatically by the TX white label.
    Source: Texas Tax Code § 11.13(a)–(b)
    https://statutes.capitol.texas.gov/Docs/TX/htm/TX.11.htm#11.13

    Benefit amount:
    - $400/year (base general homestead exemption: $100,000 reduction in
      appraised value × statewide average school district tax rate of ~$0.40/$100)
    - $600/year for seniors (age 65+) or people with disabilities (additional
      $10,000 exemption on top of the general exemption, same rate applied)
    Source: Texas Tax Code § 11.13(b) (general), § 11.13(c)–(d) (senior/disabled)
    https://statutes.capitol.texas.gov/Docs/TX/htm/TX.11.htm#11.13
    """
    amount = 400
    senior_disabled_amount = 600
    senior_age = 65
    dependencies: ClassVar[list[str]] = ["age"]

    def household_eligible(self, e: Eligibility):
        e.condition(self.screen.has_expense(["mortgage"]))

    def household_value(self) -> int:
        for member in self.screen.household_members.all():
            if member.age is not None and member.age >= self.senior_age:
                return self.senior_disabled_amount
            if member.has_disability():
                return self.senior_disabled_amount
        return self.amount
