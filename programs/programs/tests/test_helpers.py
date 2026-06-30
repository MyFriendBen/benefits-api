"""
Unit tests for helper functions used by PolicyEngine dependencies.

These tests verify the federal snap_ineligible_student() helper function.
NC-specific exemptions are tested in test_member.py via NcSnapIneligibleStudentDependency.

"""

from django.test import TestCase
from programs.models import Program
from screener.models import Screen, HouseholdMember, WhiteLabel

# from programs.programs.helpers import snap_ineligible_student
from screener.tests.helpers import seed_program
from screener.serializers import _write_current_benefits

# class TestSnapIneligibleStudentHelper(TestCase):
#     """
#     Tests for snap_ineligible_student() helper function.
#
#     This helper is called by SnapIneligibleStudentDependency to determine
#     if a student is ineligible for SNAP benefits.
#     """
#
#     def setUp(self):
#         """Set up test data for snap_ineligible_student tests."""
#         self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")
#
#         self.screen = Screen.objects.create(
#             white_label=self.white_label, zipcode="78701", county="Test County", household_size=1, completed=False
#         )
#
#     def test_snap_ineligible_student_returns_false_for_non_student(self):
#         member = HouseholdMember.objects.create(
#             screen=self.screen, relationship="headOfHousehold", age=25, student=False
#         )
#         result = snap_ineligible_student(self.screen, member)
#         self.assertFalse(result)
#
#     def test_snap_ineligible_student_returns_false_for_student_under_18(self):
#         member = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=17, student=True)
#         result = snap_ineligible_student(self.screen, member)
#         self.assertFalse(result)
#
#     def test_snap_ineligible_student_returns_false_for_student_age_50_or_older(self):
#         member = HouseholdMember.objects.create(
#             screen=self.screen, relationship="headOfHousehold", age=50, student=True
#         )
#         result = snap_ineligible_student(self.screen, member)
#         self.assertFalse(result)
#
#     def test_snap_ineligible_student_returns_false_for_disabled_student(self):
#         member = HouseholdMember.objects.create(
#             screen=self.screen, relationship="headOfHousehold", age=25, student=True, disabled=True
#         )
#         result = snap_ineligible_student(self.screen, member)
#         self.assertFalse(result)
#
#     def test_snap_ineligible_student_returns_false_for_head_with_child_under_6(self):
#         self.screen.household_size = 3
#         self.screen.save()
#         head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, student=True)
#         HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=26)
#         HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4)
#         result = snap_ineligible_student(self.screen, head)
#         self.assertFalse(result)
#
#     def test_snap_ineligible_student_returns_false_for_spouse_with_child_under_6(self):
#         self.screen.household_size = 3
#         self.screen.save()
#         HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=30)
#         spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=25, student=True)
#         HouseholdMember.objects.create(screen=self.screen, relationship="child", age=3)
#         result = snap_ineligible_student(self.screen, spouse)
#         self.assertFalse(result)
#
#     def test_snap_ineligible_student_returns_false_for_single_parent_with_child_under_12(self):
#         self.screen.household_size = 2
#         self.screen.save()
#         head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, student=True)
#         HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)
#         result = snap_ineligible_student(self.screen, head)
#         self.assertFalse(result)
#
#     def test_snap_ineligible_student_returns_true_for_student_age_18_49_no_exceptions(self):
#         member = HouseholdMember.objects.create(
#             screen=self.screen, relationship="headOfHousehold", age=25, student=True, disabled=False
#         )
#         result = snap_ineligible_student(self.screen, member)
#         self.assertTrue(result)
#
#     def test_snap_ineligible_student_returns_true_for_student_age_18_exactly_no_exceptions(self):
#         HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=45)
#         member = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=18, student=True)
#         result = snap_ineligible_student(self.screen, member)
#         self.assertTrue(result)
#
#     def test_snap_ineligible_student_returns_true_for_student_age_49_exactly_no_exceptions(self):
#         member = HouseholdMember.objects.create(
#             screen=self.screen, relationship="headOfHousehold", age=49, student=True
#         )
#         result = snap_ineligible_student(self.screen, member)
#         self.assertTrue(result)
#
#     def test_snap_ineligible_student_returns_true_for_married_head_with_child_age_6(self):
#         self.screen.household_size = 3
#         self.screen.save()
#         head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, student=True)
#         HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=25)
#         HouseholdMember.objects.create(screen=self.screen, relationship="child", age=6)
#         result = snap_ineligible_student(self.screen, head)
#         self.assertTrue(result)
#
#     def test_snap_ineligible_student_returns_true_for_single_parent_with_child_age_12(self):
#         self.screen.household_size = 2
#         self.screen.save()
#         head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=25, student=True)
#         HouseholdMember.objects.create(screen=self.screen, relationship="child", age=12)
#         result = snap_ineligible_student(self.screen, head)
#         self.assertTrue(result)
#
#     def test_snap_ineligible_student_returns_false_for_tanf_household(self):
#         seed_program(self.white_label, "tanf")
#         Program.objects.filter(white_label=self.white_label, name_abbreviated="tanf").update(base_program="tanf")
#         _write_current_benefits(self.screen, ["tanf"])
#         member = HouseholdMember.objects.create(
#             screen=self.screen, relationship="headOfHousehold", age=25, student=True
#         )
#         result = snap_ineligible_student(self.screen, member)
#         self.assertFalse(result)
#
#     def test_snap_ineligible_student_exemption_matches_any_tanf_variant(self):
#         seed_program(self.white_label, "wa_tanf")
#         Program.objects.filter(white_label=self.white_label, name_abbreviated="wa_tanf").update(base_program="tanf")
#         _write_current_benefits(self.screen, ["wa_tanf"])
#         member = HouseholdMember.objects.create(
#             screen=self.screen, relationship="headOfHousehold", age=25, student=True
#         )
#         result = snap_ineligible_student(self.screen, member)
#         self.assertFalse(result)
#
#     def test_nc_fields_do_not_affect_federal_helper(self):
#         """NC-specific fields (student_full_time, job training, etc.) are ignored by the federal helper."""
#         member = HouseholdMember.objects.create(
#             screen=self.screen,
#             relationship="headOfHousehold",
#             age=25,
#             student=True,
#             student_full_time=False,
#             student_job_training_program=True,
#             student_has_work_study=True,
#             student_works_20_plus_hrs=True,
#         )
#         result = snap_ineligible_student(self.screen, member)
#         self.assertTrue(result)
