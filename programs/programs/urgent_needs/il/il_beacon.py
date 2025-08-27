from ..base import UrgentNeedFunction


class il_beacon(UrgentNeedFunction):
    dependencies = ["age"]
    min_age = 5
    max_age = 21

    def eligible(self):
        # Check if household has marked mental health or child development help
        needs_mental_health = self.screen.needs_mental_health_help
        needs_child_dev = self.screen.needs_child_dev_help

        # Check if at least one household member is between 5-21
        has_eligible_age_member = False
        for member in self.screen.household_members.all():
            if member.age is not None and self.min_age <= member.age <= self.max_age:
                has_eligible_age_member = True
                break

        # Return True if both conditions are met
        return (needs_mental_health or needs_child_dev) and has_eligible_age_member
