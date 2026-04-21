from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel, IncomeStream


class TestIsDependent(TestCase):
    """Tests for HouseholdMember.is_dependent() — qualifying child and qualifying relative."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            completed=False,
            last_tax_filing_year="2024",
        )
        self.head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=41,
        )

    # Qualifying Child

    def test_qualifying_child_under_18(self):
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=7)
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=40000, frequency="yearly"
        )
        self.assertTrue(child.is_dependent())

    def test_qualifying_child_student_under_24(self):
        student = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=21, student=True)
        self.assertTrue(student.is_dependent())

    def test_qualifying_child_disabled(self):
        disabled_adult = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=30, disabled=True
        )
        self.assertTrue(disabled_adult.is_dependent())

    # Qualifying Relative

    def test_qualifying_relative_below_threshold(self):
        adult_child = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=19, student=False
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=adult_child, type="wages", amount=1000, frequency="yearly"
        )
        self.assertTrue(adult_child.is_dependent())

    def test_qualifying_relative_exactly_at_threshold(self):
        # IRS rule is "less than" — at threshold should NOT be a dependent
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=19)
        IncomeStream.objects.create(
            screen=self.screen, household_member=adult_child, type="wages", amount=5050, frequency="yearly"
        )
        self.assertFalse(adult_child.is_dependent())

    def test_qualifying_relative_above_threshold(self):
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=19)
        IncomeStream.objects.create(
            screen=self.screen, household_member=adult_child, type="wages", amount=5051, frequency="yearly"
        )
        self.assertFalse(adult_child.is_dependent())

    def test_elderly_parent_low_income(self):
        parent = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=70)
        IncomeStream.objects.create(
            screen=self.screen, household_member=parent, type="sSRetirement", amount=4000, frequency="yearly"
        )
        self.assertTrue(parent.is_dependent())

    # Head and Spouse

    def test_head_is_never_dependent(self):
        self.assertFalse(self.head.is_dependent())

    def test_spouse_is_never_dependent(self):
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=39)
        IncomeStream.objects.create(
            screen=self.screen, household_member=spouse, type="wages", amount=0, frequency="yearly"
        )
        self.assertFalse(spouse.is_dependent())

    # Multiple members

    def test_multiple_qualifying_relatives(self):
        adult1 = HouseholdMember.objects.create(screen=self.screen, relationship="relatedOther", age=25)
        adult2 = HouseholdMember.objects.create(screen=self.screen, relationship="sisterOrBrother", age=28)
        self.assertTrue(adult1.is_dependent())
        self.assertTrue(adult2.is_dependent())

    def test_member_with_no_income(self):
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=20)
        self.assertTrue(adult_child.is_dependent())

    # MFB-307 regression

    def test_mfb_307_texas_family(self):
        """The bug scenario: 19yo with $0 income should stay in the main tax unit."""
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=39)
        child19 = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=19, student=False
        )
        child7 = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=7)

        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=43800, frequency="yearly"
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=spouse, type="wages", amount=18000, frequency="yearly"
        )

        self.assertTrue(child19.is_dependent())
        self.assertTrue(child7.is_dependent())

        dependents = [m for m in self.screen.household_members.all() if m.is_dependent()]
        self.assertEqual(len(dependents), 2)

    # Other relatives and non-relatives

    def test_aunt_with_low_income(self):
        aunt = HouseholdMember.objects.create(screen=self.screen, relationship="relatedOther", age=50)
        IncomeStream.objects.create(
            screen=self.screen, household_member=aunt, type="wages", amount=2000, frequency="yearly"
        )
        self.assertTrue(aunt.is_dependent())

    def test_roommate_with_no_income(self):
        roommate = HouseholdMember.objects.create(screen=self.screen, relationship="roommate", age=30)
        self.assertTrue(roommate.is_dependent())

    def test_grandchild_low_income(self):
        grandchild = HouseholdMember.objects.create(screen=self.screen, relationship="grandChild", age=20)
        IncomeStream.objects.create(
            screen=self.screen, household_member=grandchild, type="wages", amount=1000, frequency="yearly"
        )
        self.assertTrue(grandchild.is_dependent())

    def test_disabled_adult_at_threshold_margin(self):
        IncomeStream.objects.create(
            screen=self.screen, household_member=self.head, type="wages", amount=100000, frequency="yearly"
        )
        disabled_adult = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=30, disabled=True
        )
        IncomeStream.objects.create(
            screen=self.screen, household_member=disabled_adult, type="wages", amount=5000, frequency="yearly"
        )
        self.assertTrue(disabled_adult.is_dependent())
