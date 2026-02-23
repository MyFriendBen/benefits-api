from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


class MaTaxiDiscount(ProgramCalculator):
    """
    Cambridge Taxi Discount Coupon Program

    Provides taxi discount coupons to eligible Cambridge residents.

    Eligibility requirements that can be verified:
    - Cambridge resident (city residency via county field)
    - Age 60+ OR has a disability

    Requirements that cannot be verified programmatically:
    - Registration required before receiving coupons
    - Formal disability documentation required if under 60 (verified at registration)

    Source: https://www.cambridgema.gov/services/cambridgetaxidiscountcouponprogram
    """

    member_amount = 50 * 12  # $600/year per eligible person
    eligible_city = "Cambridge"
    min_age = 60
    dependencies = ["zipcode", "age", "disabled", "visually_impaired", "long_term_disability"]

    def household_eligible(self, e: Eligibility) -> None:
        # Check if user already has this benefit
        e.condition(not self.screen.has_benefit("ma_taxi_discount"))

        # Location check - must be Cambridge resident
        # (MA stores city name in county field, see MFB-548)
        is_cambridge = self.screen.county == self.eligible_city
        e.condition(is_cambridge, messages.location())

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member

        # Age 60+ OR has a disability
        is_senior = member.age >= self.min_age
        has_disability = member.has_disability()

        e.condition(is_senior or has_disability)
