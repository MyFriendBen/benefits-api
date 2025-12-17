from datetime import datetime
from ..base import UrgentNeedFunction

NOTIFICATION_MAX_AGE = 5


class FirstStepSavings(UrgentNeedFunction):
    """
    First Step additional resource for Colorado.
    Eligible if household:
    1. Has children aged 6-7
    2. Child has eligible relationship: child, foster child, stepchild, grandchild
    3. Does NOT have children aged 0-5 (those get FirstStepSavingsNotifiable instead)
    """

    dependencies = ["age", "relationship"]

    # Eligible child relationships
    eligible_relationships = ["child", "fosterChild", "stepChild", "grandChild"]

    def eligible(self):
        """
        Return True if household has indicated interest in savings and
        has eligible children aged 6-7, but NOT if they're eligible for
        FirstStepSavingsNotifiable (children aged 0-5)
        """
        # Check for eligible children aged 6-7
        if not self._has_eligible_children():
            return False

        # Exclude if eligible for FirstStepSavingsNotifiable (has children 0-5)
        if self._has_notification_eligible_children():
            return False

        return True

    def _has_eligible_children(self):
        """
        Check if household has children aged 6-7 with eligible relationships.
        """
        for member in self.screen.household_members.all():
            # Check relationship eligibility
            if member.relationship not in self.eligible_relationships:
                continue

            # Check age eligibility (6-7 years old)
            if member.age is not None and 6 <= member.age <= 7:
                return True

        return False

    def _has_notification_eligible_children(self):
        """
        Check if household has children aged 0-5 with eligible relationships.
        This is used to determine exclusion from regular FirstStepSavings.
        """
        for member in self.screen.household_members.all():
            # Check relationship eligibility
            if member.relationship not in self.eligible_relationships:
                continue

            # Check age eligibility (0-5 years old)
            if member.age is not None and member.age <= NOTIFICATION_MAX_AGE:
                return True

        return False


class FirstStepSavingsNotifiable(FirstStepSavings):
    """
    Special version for the notification banner on results page.
    Only shows for households with children aged 0-5.
    If a household is eligible for this, they are NOT eligible for regular FirstStepSavings.
    """

    def eligible(self):
        """
        Return True if household has eligible children aged 0-5
        """
        # Check for eligible children aged 0-5
        return self._has_eligible_children()

    def _has_eligible_children(self):
        """
        Check if household has children aged 0-5 with eligible relationships.
        This is a subset of the full First Step eligibility for the notification banner.
        """
        for member in self.screen.household_members.all():
            # Check relationship eligibility
            if member.relationship not in self.eligible_relationships:
                continue

            # Check age eligibility (0-5 years old for notification)
            if member.age is not None and member.age <= NOTIFICATION_MAX_AGE:
                return True

        return False
