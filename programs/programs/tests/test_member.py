"""
Unit tests for member-level PolicyEngine dependency classes.
"""

from django.test import TestCase
from screener.models import Screen, HouseholdMember, WhiteLabel
from programs.programs.policyengine.calculators.dependencies.member import NcSnapIneligibleStudentDependency


class TestNcSnapIneligibleStudentDependency(TestCase):
    """
    Tests for NcSnapIneligibleStudentDependency.value().

    This dependency is used by NcSnap.pe_inputs and applies NC-specific SNAP
    student exemptions on top of the standard federal E1–E6 exemptions.
    """

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test NC", code="nc", state_code="NC")
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="27601",
            county="Wake",
            household_size=1,
            completed=False,
        )

    def _dep(self, member):
        return NcSnapIneligibleStudentDependency(self.screen, member, self.screen.relationship_map())

    # ── Student gate ──────────────────────────────────────────────────────────

    def test_non_student_is_eligible(self):
        """Non-students are never subject to the restriction."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=25, student=False
        )
        self.assertFalse(self._dep(member).value())

    # ── NC part-time exemption ────────────────────────────────────────────────

    def test_part_time_student_is_exempt(self):
        """NC part-time student (student_full_time=False) is fully exempt."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_full_time=False,
            student_job_training_program=False,
            student_has_work_study=False,
            student_works_20_plus_hrs=False,
        )
        self.assertFalse(self._dep(member).value())

    # ── Federal E1/E2: age exemptions ─────────────────────────────────────────

    def test_full_time_student_under_18_is_exempt(self):
        """Full-time student under 18 is exempt (E1)."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="child", age=17, student=True, student_full_time=True
        )
        self.assertFalse(self._dep(member).value())

    def test_full_time_student_age_50_is_exempt(self):
        """Full-time student aged 50+ is exempt (E2)."""
        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=50, student=True, student_full_time=True
        )
        self.assertFalse(self._dep(member).value())

    # ── Federal E3: disability ────────────────────────────────────────────────

    def test_disabled_student_is_exempt(self):
        """Disabled full-time student is exempt (E3)."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_full_time=True,
            disabled=True,
        )
        self.assertFalse(self._dep(member).value())

    # ── Federal E4: parent with child under 6 ─────────────────────────────────

    def test_head_with_child_under_6_is_exempt(self):
        """Head of household with child under 6 is exempt (E4)."""
        self.screen.household_size = 3
        self.screen.save()

        head = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=25, student=True, student_full_time=True
        )
        HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=26)
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=4)

        self.assertFalse(self._dep(head).value())

    # ── Federal E5: single parent with child under 12 ─────────────────────────

    def test_single_parent_with_child_under_12_is_exempt(self):
        """Single parent with child under 12 is exempt (E5)."""
        self.screen.household_size = 2
        self.screen.save()

        head = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=25, student=True, student_full_time=True
        )
        HouseholdMember.objects.create(screen=self.screen, relationship="child", age=10)

        self.assertFalse(self._dep(head).value())

    # ── Federal E6: TANF ──────────────────────────────────────────────────────

    def test_tanf_household_is_exempt(self):
        """Student in a household receiving TANF/Work First is exempt (E6)."""
        self.screen.has_tanf = True
        self.screen.save()

        member = HouseholdMember.objects.create(
            screen=self.screen, relationship="headOfHousehold", age=25, student=True, student_full_time=True
        )
        self.assertFalse(self._dep(member).value())

    # ── NC Step 3: employment exemptions ──────────────────────────────────────

    def test_job_training_program_is_exempt(self):
        """Student in a job training program is exempt (NC Step 3)."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_job_training_program=True,
        )
        self.assertFalse(self._dep(member).value())

    def test_work_study_is_exempt(self):
        """Student with federal work study is exempt (NC Step 3)."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_has_work_study=True,
        )
        self.assertFalse(self._dep(member).value())

    def test_works_20_plus_hours_is_exempt(self):
        """Student working 20+ hours per week is exempt (NC Step 3)."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_works_20_plus_hrs=True,
        )
        self.assertFalse(self._dep(member).value())

    # ── Ineligible path ───────────────────────────────────────────────────────

    def test_ineligible_when_no_exemption_applies(self):
        """Full-time student with no exemptions is excluded from the SNAP unit."""
        member = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=25,
            student=True,
            student_full_time=True,
            student_job_training_program=False,
            student_has_work_study=False,
            student_works_20_plus_hrs=False,
        )
        self.assertTrue(self._dep(member).value())
