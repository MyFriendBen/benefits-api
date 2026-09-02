"""Shared member-value rule for Illinois transit programs.

Transit Reduced Fare and Benefit Access both value the benefit per qualifying
member rather than per household."""

from programs.framework.base import Eligibility, MemberEligibility


class IlTransportationMixin:
    dependencies = [
        "age",
        "visually_impaired",
        "disabled",
    ]
    minimum_age = 65
    minimum_age_with_disability = 16

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        age_eligible = member.age >= self.minimum_age

        has_minimum_age_with_disability = member.age >= self.minimum_age_with_disability
        has_eligible_disability = member.visually_impaired or member.disabled
        disability_eligible = has_minimum_age_with_disability and has_eligible_disability

        e.condition(age_eligible or disability_eligible)

    def member_value(self, member):
        # Default to positive value to enable manual "Varies" override
        return 1
