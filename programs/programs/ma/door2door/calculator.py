from programs.programs.calc import ProgramCalculator, Eligibility, MemberEligibility
import programs.programs.messages as messages


class MaDoorToDoor(ProgramCalculator):
    """
    Door2Door Transportation (SCM) - Cambridge eligibility

    Door2Door Transportation provides on-demand rides to medical appointments
    and grocery stores for eligible Cambridge residents.

    Eligibility requirements:
    - Cambridge resident
    - Age 60+ OR has a mobility impairment

    Value: Not a fixed dollar benefit; value is access to rides for key needs.
    We return 1 to indicate eligibility; frontend displays "Varies".

    Source: https://www.scmtransportation.org/services-by-city.html
    """

    amount = 1
    eligible_city = "Cambridge"
    min_age = 60
    dependencies = ["zipcode", "age"]

    def household_eligible(self, e: Eligibility):
        # Check if user already has this benefit
        e.condition(not self.screen.has_benefit("ma_door_to_door"))

        # Location check - must be Cambridge resident
        is_cambridge = self.screen.county == self.eligible_city
        e.condition(is_cambridge, messages.location())

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Age 60+ OR has a mobility impairment (disability)
        is_senior = member.age >= self.min_age
        has_mobility_impairment = member.has_disability()

        e.condition(is_senior or has_mobility_impairment)
