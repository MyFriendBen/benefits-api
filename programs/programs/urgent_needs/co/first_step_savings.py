from datetime import datetime
from ..base import UrgentNeedFunction


class FirstStepSavings(UrgentNeedFunction):
    """
    First Step additional resource for Colorado.
    Eligible if household:
    1. Has children aged 0-7 (born on/after Jan 1, 2020)
    2. Child has eligible relationship: child, foster child, stepchild, grandchild
    """

    dependencies = ["age", "relationship"]

    # Eligible child relationships
    eligible_relationships = ["child", "fosterChild", "stepChild", "grandChild"]

    def eligible(self):
        """
        Return True if household has indicated interest in savings and
        has eligible children aged 0-7, but NOT if they're eligible for
        FirstStepSavingsNotifiable (children aged 0-2)
        """
        # Check for eligible children
        if not self._has_eligible_children():
            return False

        # Exclude if eligible for FirstStepSavingsNotifiable (has children 0-2)
        if self._has_children_aged_0_to_2():
            return False

        return True

    def _has_eligible_children(self):
        """
        Check if household has children aged 0-7 with eligible relationships.
        Children must be born on or after January 1, 2020.
        """
        # Calculate the cutoff date - children born on/after Jan 1, 2020
        cutoff_date = datetime(2020, 1, 1)

        for member in self.screen.household_members.all():
            # Check relationship eligibility
            if member.relationship not in self.eligible_relationships:
                continue

            # Check age eligibility (0-7 years old)
            # First check if they have birth_year_month
            if member.birth_year_month:
                # Child must be born on or after Jan 1, 2020
                if member.birth_year_month >= cutoff_date.date():
                    # Also check they're not 8 yet
                    age = member.calc_age()
                    if age < 8:
                        return True
            # Fall back to age field if no birth date
            elif member.age is not None and member.age < 8:
                # Conservative check - child under 8 could be eligible
                return True

        return False

    def _has_children_aged_0_to_2(self):
        """
        Check if household has children aged 0-2 with eligible relationships.
        This is used to determine exclusion from regular FirstStepSavings.
        """
        for member in self.screen.household_members.all():
            # Check relationship eligibility
            if member.relationship not in self.eligible_relationships:
                continue

            # Check age eligibility (0-2 years old)
            if member.age is not None and member.age <= 2:
                return True

        return False


class FirstStepSavingsNotifiable(FirstStepSavings):
    """
    Special version for the notification banner on results page.
    Only shows for households with children aged 0-2.
    If a household is eligible for this, they are NOT eligible for regular FirstStepSavings.
    """

    def eligible(self):
        """
        Return True if household has indicated interest in savings and
        has eligible children aged 0-2
        """

        # Check for eligible children aged 0-2
        return self._has_eligible_children()

    def _has_eligible_children(self):
        """
        Check if household has children aged 0-2 with eligible relationships.
        This is a subset of the full First Step eligibility for the notification.
        """
        for member in self.screen.household_members.all():
            # Check relationship eligibility
            if member.relationship not in self.eligible_relationships:
                continue

            # Check age eligibility (0-2 years old for notification)
            if member.age is not None and member.age <= 2:
                return True

        return False
