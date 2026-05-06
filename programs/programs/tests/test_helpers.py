"""
Unit tests for helper functions used by PolicyEngine dependencies.

These tests verify helper functions that are called by TxSnap dependencies.
"""

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel
from programs.programs.helpers import snap_ineligible_student
from programs.programs.policyengine.calculators.dependencies import member


class TestSnapIneligibleStudentHelper(TestCase):
    """
    Tests for snap_ineligible_student() helper function.

    This helper is called by SnapIneligibleStudentDependency to determine
    if a student is ineligible for SNAP benefits.
    """

    def setUp(self):
        """Set up test data for snap_ineligible_student tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="78701", county="Test County", household_size=1, completed=False
        )

    def test_snap_ineligible_student_returns_false_for_non_student(self):
        """Test that non-students are eligible (returns False)."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=25, student=False
        )

        result = snap_ineligible_student(self.screen, member)
        self.assertFalse(result)

    def test_snap_ineligible_student_returns_false_for_student_under_18(self):
        """Test that students under 18 are eligible (returns False)."""
        member = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=17, student=True)

        result = snap_ineligible_student(self.screen, member)
        self.assertFalse(result)

    def test_snap_ineligible_student_returns_false_for_student_age_50_or_older(self):
        """Test that students 50+ are eligible (returns False)."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=50, student=True
        )

        result = snap_ineligible_student(self.screen, member)
        self.assertFalse(result)

    def test_snap_ineligible_student_returns_false_for_disabled_student(self):
        """Test that disabled students are eligible (returns False)."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=25, student=True, disabled=True
        )

        result = snap_ineligible_student(self.screen, member)
        self.assertFalse(result)

    def test_snap_ineligible_student_returns_false_for_head_with_child_under_6(self):
        """Test that head of household with child under 6 is eligible (returns False)."""
        self.screen.household_size = 3
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, student=True)

        # Add spouse to make head married
        HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=26)

        # Add child under 6
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4)

        result = snap_ineligible_student(self.screen, head)
        self.assertFalse(result)

    def test_snap_ineligible_student_returns_false_for_spouse_with_child_under_6(self):
        """Test that spouse with child under 6 is eligible (returns False)."""
        self.screen.household_size = 3
        self.screen.save()

        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)

        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=25, student=True)

        # Add child under 6
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=3)

        result = snap_ineligible_student(self.screen, spouse)
        self.assertFalse(result)

    def test_snap_ineligible_student_returns_false_for_single_parent_with_child_under_12(self):
        """Test that single parent with child under 12 is eligible (returns False)."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, student=True)
        # No spouse = single parent

        # Add child under 12
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

        result = snap_ineligible_student(self.screen, head)
        self.assertFalse(result)

    def test_snap_ineligible_student_returns_true_for_student_age_18_49_no_exceptions(self):
        """Test that student age 18-49 with no exceptions is ineligible (returns True)."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=25, student=True, disabled=False
        )
        # No spouse or children = no exceptions

        result = snap_ineligible_student(self.screen, member)
        self.assertTrue(result)

    def test_snap_ineligible_student_returns_true_for_student_age_18_exactly_no_exceptions(self):
        """Test edge case: student exactly age 18 with no exceptions is ineligible."""
        # Need head of household for relationship_map
        HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=45)

        member = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=18, student=True)

        result = snap_ineligible_student(self.screen, member)
        self.assertTrue(result)

    def test_snap_ineligible_student_returns_true_for_student_age_49_exactly_no_exceptions(self):
        """Test edge case: student exactly age 49 with no exceptions is ineligible."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=49, student=True
        )

        result = snap_ineligible_student(self.screen, member)
        self.assertTrue(result)

    def test_snap_ineligible_student_returns_true_for_married_head_with_child_age_6(self):
        """Test that married head with child age 6 (not under 6) is ineligible."""
        self.screen.household_size = 3
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, student=True)

        # Add spouse to make head married
        HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=25)

        # Child is exactly 6 (not under 6)
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=6)

        result = snap_ineligible_student(self.screen, head)
        self.assertTrue(result)

    def test_snap_ineligible_student_returns_true_for_single_parent_with_child_age_12(self):
        """Test that single parent with child age 12 (not under 12) is ineligible."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, student=True)
        # No spouse = single parent

        # Child is exactly 12 (not under 12)
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=12)

        result = snap_ineligible_student(self.screen, head)
        self.assertTrue(result)


class TestSnapIneligibleStudentHelperNC(TestCase):
    """
    Tests for snap_ineligible_student() helper function.

    This helper is called by SnapIneligibleStudentDependency to determine
    if a student is ineligible for SNAP benefits for NC state.
    """

    def setUp(self):
        """Set up test data for snap_ineligible_student tests."""
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="NC")

        self.screen = Screen.objects.create(
            white_label=self.white_label, zipcode="27601", county="Test County", household_size=1, completed=False
        )
    
    def test_exempt_when_full_time_student_single_parent_with_child(self):
        """Test that NC full-time student single parent with child under 12 is exempt."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, student=True, student_full_time=True)
        # No spouse = single parent

        # Add child under 12
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

        result = snap_ineligible_student(self.screen, head)
        self.assertFalse(result)

    def test_not_exempt_when_part_time_student_single_parent_with_child(self):
        """NC part-time student single parent with child under 12 is NOT exempt via E5."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_full_time=False,  # NC explicitly collected as part-time
        )
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=8)

        result = snap_ineligible_student(self.screen, head)
        self.assertTrue(result)   # E5 does NOT apply, no other exemption → ineligible

    def test_exempt_via_job_training_program(self):
        """Student in job training program is exempt from SNAP student restriction."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_job_training_program=True,
        )
        result = snap_ineligible_student(self.screen, member)
        self.assertFalse(result)   # job training → exempt

    def test_exempt_via_work_study(self):
        """Student with federal work study is exempt from SNAP student restriction."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_has_work_study=True,
        )
        result = snap_ineligible_student(self.screen, member)
        self.assertFalse(result)   # work study → exempt

    def test_exempt_via_works_20_plus_hours(self):
        """Student working 20+ hours per week is exempt from SNAP student restriction."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_works_20_plus_hrs=True,
        )
        result = snap_ineligible_student(self.screen, member)
        self.assertFalse(result)   # 20+ hrs → exempt

    def test_ineligible_when_all_step3_fields_are_false(self):
        """Student with all employment fields explicitly False is ineligible."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_job_training_program=False,
            student_has_work_study=False,
            student_works_20_plus_hrs=False,
        )
        result = snap_ineligible_student(self.screen, member)
        self.assertTrue(result)   # no exemption met → ineligible

class TestFullTimeCollegeStudentDependency(TestCase):
    """Tests for FullTimeCollegeStudentDependency.value()."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test NC", code="nc", state_code="NC")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="27601",
            county="Wake",
            household_size=1,
            completed=False,
        )

    def test_falls_back_to_student_true_when_full_time_is_none(self):
        """When student_full_time is None (not collected), fall back to student field."""
        head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=22,
            student=True,
            student_full_time=None,
        )
        dep = member.FullTimeCollegeStudentDependency(self.screen, head, {})
        self.assertTrue(dep.value())


    def test_falls_back_to_student_false_when_full_time_is_none(self):
        """When student_full_time is None, fall back returns False if student is False."""
        head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=22,
            student=False,
            student_full_time=None,
        )
        dep = member.FullTimeCollegeStudentDependency(self.screen, head, {})
        self.assertFalse(dep.value())


    def test_uses_student_full_time_true_over_student_false(self):
        """student_full_time=True takes priority even if student=False."""
        head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=22,
            student=False,          # would return False without the new logic
            student_full_time=True, # new field wins
        )
        dep = member.FullTimeCollegeStudentDependency(self.screen, head, {})
        self.assertTrue(dep.value())


    def test_uses_student_full_time_false_over_student_true(self):
        """student_full_time=False takes priority even if student=True."""
        head = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=22,
            student=True,            # would return True without the new logic
            student_full_time=False, # new field wins
        )
        dep = member.FullTimeCollegeStudentDependency(self.screen, head, {})
        self.assertFalse(dep.value())
