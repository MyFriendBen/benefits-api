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
    Source: Texas Tax Code § 11.13(j) (definition of residence homestead)
    https://statutes.capitol.texas.gov/Docs/TX/htm/TX.11.htm#11.13

    Benefit amount:
    - $400/year (estimated typical tax savings for a low-income TX homeowner
      with a ~$120K home value under the general homestead exemption)
    - $600/year for seniors (age 65+) or people with disabilities (estimated
      typical savings under the general + senior/disabled exemption combined)
    Note: actual savings vary by taxing unit and appraised value.

    Disability eligibility follows the SSA test (Texas Tax Code § 11.13):
    - Medically determinable physical or mental impairment (proxied by long_term_disability)
    - Impairment prevents substantial gainful activity
    - Impairment expected to last at least 12 continuous months or result in death
    Also qualifies: age >= 55 and visually impaired, and cannot engage in previous
    work due to blindness.
    Source: https://statutes.capitol.texas.gov/?tab=1&code=TX&chapter=TX.11&artSec=
    """

    amount = 400
    senior_disabled_amount = 600
    senior_age = 65
    blind_senior_age = 55
    dependencies: ClassVar[list[str]] = ["age"]

    def _qualifies_for_disability_exemption(self, member) -> bool:
        """
        Returns True if the member qualifies for the disability-based higher exemption
        under Texas Tax Code § 11.13(m).
        Source: https://statutes.capitol.texas.gov/?tab=1&code=TX&chapter=TX.11&artSec=

        Two paths to qualify:

        1. SSA disability test — either screener field satisfies this:
           - long_term_disability: medical/developmental condition lasting or expected
             to last 12+ months (satisfies the duration + medically determinable criteria)
           - disabled: unable to work now or in the future (satisfies the substantial
             gainful activity criterion)

        2. Age 55+ and visually impaired — cannot engage in previous work due to blindness.
        """
        if member.long_term_disability or member.disabled:
            return True
        if member.visually_impaired and member.age is not None and member.age >= self.blind_senior_age:
            return True
        return False

    def household_eligible(self, e: Eligibility):
        e.condition(self.screen.has_expense(["mortgage"]))

    def household_value(self) -> int:
        for member in self.screen.household_members.all():
            if member.age is not None and member.age >= self.senior_age:
                return self.senior_disabled_amount
            if self._qualifies_for_disability_exemption(member):
                return self.senior_disabled_amount
        return self.amount
