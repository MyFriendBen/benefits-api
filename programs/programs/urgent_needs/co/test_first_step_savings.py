from datetime import datetime, date
from django.test import TestCase
from programs.models import UrgentNeed
from programs.programs.urgent_needs.co.first_step_savings import FirstStepSavings, FirstStepSavingsNotifiable
from screener.models import Screen, HouseholdMember, WhiteLabel
from translations.models import Translation
from programs.util import Dependencies


class TestFirstStepSavings(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create a white label for Colorado
        self.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")

        # Create required translations
        name_translation = Translation.objects.add_translation("test_urgent_need.first_step.name", "Test First Step")
        description_translation = Translation.objects.add_translation(
            "test_urgent_need.first_step.description", "Test Description"
        )
        link_translation = Translation.objects.add_translation(
            "test_urgent_need.first_step.link", "https://example.com"
        )
        website_description_translation = Translation.objects.add_translation(
            "test_urgent_need.first_step.website_description", "Test Website Description"
        )
        warning_translation = Translation.objects.add_translation("test_urgent_need.first_step.warning", "Test Warning")
        notification_message_translation = Translation.objects.add_translation(
            "test_urgent_need.first_step.notification_message", "Test Notification"
        )

        # Create a mock urgent need
        self.urgent_need = UrgentNeed.objects.create(
            white_label=self.white_label,
            external_name="first_step",
            name=name_translation,
            description=description_translation,
            link=link_translation,
            website_description=website_description_translation,
            warning=warning_translation,
            notification_message=notification_message_translation,
        )

        # Create a base screen
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="80205",
            county="Denver County",
            household_size=3,
            household_assets=0,
            needs_college_savings=True,  # Household interested in savings
            completed=False,
        )

        # Create head of household
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=30,
            student=False,
            pregnant=False,
            unemployed=False,
            disabled=False,
            veteran=False,
        )

    def test_eligible_with_young_child(self):
        """Test eligibility when household has a young child with eligible relationship (6+ years old)"""
        # Add a 6-year-old child (eligible for FirstStepSavings, not FirstStepSavingsNotifiable)
        child = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=6, birth_year_month=date(2019, 1, 1)
        )

        calculator = FirstStepSavings(self.screen, self.urgent_need, Dependencies(), {})

        self.assertTrue(calculator.eligible())

    def test_eligible_with_foster_child(self):
        """Test eligibility with foster child"""
        # Add a 7-year-old foster child
        foster_child = HouseholdMember.objects.create(
            screen=self.screen, relationship="fosterChild", age=7, birth_year_month=date(2018, 6, 1)
        )

        calculator = FirstStepSavings(self.screen, self.urgent_need, Dependencies(), {})

        self.assertTrue(calculator.eligible())

    def test_eligible_with_stepchild(self):
        """Test eligibility with stepchild"""
        # Add a 6-year-old stepchild
        stepchild = HouseholdMember.objects.create(
            screen=self.screen, relationship="stepChild", age=6, birth_year_month=date(2019, 3, 15)
        )

        calculator = FirstStepSavings(self.screen, self.urgent_need, Dependencies(), {})

        self.assertTrue(calculator.eligible())

    def test_eligible_with_grandchild(self):
        """Test eligibility with grandchild (7+ years old)"""
        # Add a 7-year-old grandchild (eligible for FirstStepSavings, not FirstStepSavingsNotifiable)
        grandchild = HouseholdMember.objects.create(
            screen=self.screen, relationship="grandChild", age=7, birth_year_month=date(2018, 1, 1)
        )

        calculator = FirstStepSavings(self.screen, self.urgent_need, Dependencies(), {})

        self.assertTrue(calculator.eligible())

    def test_not_eligible_child_too_old(self):
        """Test ineligibility when child is 8 or older"""
        # Add an 8-year-old child (too old)
        old_child = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=8, birth_year_month=date(2016, 1, 1)
        )

        calculator = FirstStepSavings(self.screen, self.urgent_need, Dependencies(), {})

        self.assertFalse(calculator.eligible())

    def test_not_eligible_no_savings_interest(self):
        """Test ineligibility when household hasn't expressed interest in savings"""
        # Set needs_college_savings to False
        self.screen.needs_college_savings = False
        self.screen.save()

        # Add an eligible child
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=2)

        calculator = FirstStepSavings(self.screen, self.urgent_need, Dependencies(), {})

        self.assertFalse(calculator.eligible())

    def test_not_eligible_wrong_relationship(self):
        """Test ineligibility when child has non-eligible relationship"""
        # Add a child with non-eligible relationship (e.g., sibling)
        sibling = HouseholdMember.objects.create(screen=self.screen, relationship="sisterOrBrother", age=2)

        calculator = FirstStepSavings(self.screen, self.urgent_need, Dependencies(), {})

        self.assertFalse(calculator.eligible())

    def test_not_eligible_with_children_0_to_5(self):
        """Test FirstStepSavings is NOT eligible when household has children aged 0-5"""
        # Add a 1-year-old child (should make NotFirstStepSavings eligible, and FirstStepSavings ineligible)
        baby = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=1)

        calculator = FirstStepSavings(self.screen, self.urgent_need, Dependencies(), {})

        # FirstStepSavings should be ineligible because household has child aged 0-2
        self.assertFalse(calculator.eligible())

    def test_eligible_with_children_6_to_7(self):
        """Test FirstStepSavings IS eligible when household has children aged 6-7 (no 0-5 children)"""
        # Add a 5-year-old child (eligible for FirstStepSavings but not NotFirstStepSavings)
        child = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=6, birth_year_month=date(2019, 6, 1)
        )

        calculator = FirstStepSavings(self.screen, self.urgent_need, Dependencies(), {})

        # FirstStepSavings should be eligible because child is 6-7 and no children 0-5
        self.assertTrue(calculator.eligible())


class TestFirstStepSavingsNotifiable(TestCase):
    def setUp(self):
        """Set up test data for notification tests"""
        # Create a white label for Colorado
        self.white_label = WhiteLabel.objects.create(name="Colorado", code="co", state_code="CO")

        # Create required translations
        name_translation = Translation.objects.add_translation(
            "test_urgent_need.first_step_notifiable.name", "Test First Step Notifiable"
        )
        description_translation = Translation.objects.add_translation(
            "test_urgent_need.first_step_notifiable.description", "Test Description"
        )
        link_translation = Translation.objects.add_translation(
            "test_urgent_need.first_step_notifiable.link", "https://example.com"
        )
        website_description_translation = Translation.objects.add_translation(
            "test_urgent_need.first_step_notifiable.website_description", "Test Website Description"
        )
        warning_translation = Translation.objects.add_translation(
            "test_urgent_need.first_step_notifiable.warning", "Test Warning"
        )
        notification_message_translation = Translation.objects.add_translation(
            "test_urgent_need.first_step_notifiable.notification_message", "Test Notification"
        )

        # Create a mock urgent need
        self.urgent_need = UrgentNeed.objects.create(
            white_label=self.white_label,
            external_name="first_step_notifiable",
            name=name_translation,
            description=description_translation,
            link=link_translation,
            website_description=website_description_translation,
            warning=warning_translation,
            notification_message=notification_message_translation,
        )

        # Create a base screen
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            agree_to_tos=True,
            zipcode="80205",
            county="Denver County",
            household_size=3,
            household_assets=0,
            needs_college_savings=True,
            completed=False,
        )

        # Create head of household
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

    def test_notification_shows_for_age_0_to_5(self):
        """Test notification shows for children aged 0-5"""
        # Add a 1-year-old child
        baby = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=1)

        calculator = FirstStepSavingsNotifiable(self.screen, self.urgent_need, Dependencies(), {})

        self.assertTrue(calculator.eligible())

    def test_notification_not_shown_for_age_6_plus(self):
        """Test notification doesn't show for children aged 3+"""
        # Add a 3-year-old child
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=6)

        calculator = FirstStepSavingsNotifiable(self.screen, self.urgent_need, Dependencies(), {})

        self.assertFalse(calculator.eligible())

    def test_notification_age_boundary(self):
        """Test notification boundary at age 5"""
        # Test with 5-year-old (should show)
        five_year_old = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=5)

        calculator = FirstStepSavingsNotifiable(self.screen, self.urgent_need, Dependencies(), {})

        self.assertTrue(calculator.eligible())

        # Clean up and test with 6-year-old (should not show)
        five_year_old.delete()
        six_year_old = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=6)

        calculator = FirstStepSavingsNotifiable(self.screen, self.urgent_need, Dependencies(), {})

        self.assertFalse(calculator.eligible())
