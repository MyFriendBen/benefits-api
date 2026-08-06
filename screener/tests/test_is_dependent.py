from django.test import TestCase
from configuration.white_labels.base import ConfigurationData
from screener.irs_parameters import get_qualifying_relative_threshold
from screener.models import (
    DEPENDENT_ELIGIBLE_RELATIONSHIPS,
    HouseholdMember,
    IncomeStream,
    Screen,
    WhiteLabel,
)

ALL_RELATIONSHIP_OPTIONS = set(ConfigurationData.relationship_options.keys())


class TestIsDependent(TestCase):
    """Tests for HouseholdMember.is_dependent() — qualifying child and qualifying relative."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Texas", code="tx", state_code="TX")
        self.screen = self._make_screen()
        self.head = HouseholdMember.objects.create(screen=self.screen, relationship="headOfHousehold", age=41)

    def _make_screen(self):
        return Screen.objects.create(
            white_label=self.white_label,
            completed=False,
        )

    def _add_yearly_income(self, member, amount, income_type="wages"):
        IncomeStream.objects.create(
            screen=member.screen,
            household_member=member,
            type=income_type,
            amount=amount,
            frequency="yearly",
        )

    def _setup_path_1_household(self, relationship):
        """Path 1 household: student under 24 with income low enough to pass ratio test."""
        screen = self._make_screen()
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=40)
        member = HouseholdMember.objects.create(screen=screen, relationship=relationship, age=21, student=True)
        self._add_yearly_income(head, 40_000)
        self._add_yearly_income(member, 6_000)
        return head, member

    def _setup_path_2_household(self, relationship, income=1_000):
        """Path 2 household: adult low-income member below qualifying-relative threshold."""
        screen = self._make_screen()
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=40)
        member = HouseholdMember.objects.create(screen=screen, relationship=relationship, age=35, student=False)
        self._add_yearly_income(member, income)
        return member

    # Qualifying Child

    def test_qualifying_child_under_18(self):
        child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=7)
        self._add_yearly_income(self.head, 40_000)
        self._add_yearly_income(child, 6_000)
        self.assertTrue(child.is_dependent())

    def test_qualifying_child_student_under_24(self):
        student = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=21, student=True)
        self._add_yearly_income(self.head, 40_000)
        self._add_yearly_income(student, 6_000)
        self.assertTrue(student.is_dependent())

    def test_qualifying_child_disabled(self):
        disabled_adult = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=30, disabled=True)
        self._add_yearly_income(self.head, 40_000)
        self._add_yearly_income(disabled_adult, 6_000)
        self.assertTrue(disabled_adult.is_dependent())

    def test_relationship_gate_applies_to_path_1_for_all_configured_relationships(self):
        for relationship in sorted(ALL_RELATIONSHIP_OPTIONS):
            with self.subTest(path="qualifying_child", relationship=relationship):
                _, member = self._setup_path_1_household(relationship)
                expected = relationship in DEPENDENT_ELIGIBLE_RELATIONSHIPS
                self.assertEqual(member.is_dependent(), expected)

    # Qualifying Relative

    def test_qualifying_relative_below_threshold(self):
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=19, student=False)
        self._add_yearly_income(adult_child, 1_000)
        self.assertTrue(adult_child.is_dependent())

    def test_qualifying_relative_exactly_at_threshold(self):
        # IRS rule is "less than" — at threshold should NOT be a dependent
        threshold = get_qualifying_relative_threshold(self.screen.get_reference_date().year)
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=19)
        self._add_yearly_income(adult_child, threshold)
        self.assertFalse(adult_child.is_dependent())

    def test_qualifying_relative_above_threshold(self):
        threshold = get_qualifying_relative_threshold(self.screen.get_reference_date().year)
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=19)
        self._add_yearly_income(adult_child, threshold + 1)
        self.assertFalse(adult_child.is_dependent())

    def test_elderly_parent_low_income(self):
        parent = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=70)
        self._add_yearly_income(parent, 4_000, income_type="sSRetirement")
        self.assertTrue(parent.is_dependent())

    def test_relationship_gate_applies_to_path_2_for_all_configured_relationships(self):
        for relationship in sorted(ALL_RELATIONSHIP_OPTIONS):
            with self.subTest(path="qualifying_relative", relationship=relationship):
                member = self._setup_path_2_household(relationship, income=1_000)
                expected = relationship in DEPENDENT_ELIGIBLE_RELATIONSHIPS
                self.assertEqual(member.is_dependent(), expected)

    # Head and Spouse

    def test_spouse_is_never_dependent(self):
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=39)
        self._add_yearly_income(spouse, 0)
        self.assertFalse(spouse.is_dependent())

    def test_domestic_partner_is_never_dependent_because_spouse_equivalent(self):
        """Domestic partner is handled by spouse-pairing and should never enter dependent logic."""
        partner = HouseholdMember.objects.create(screen=self.screen, relationship="domesticPartner", age=39)
        self._add_yearly_income(partner, 0)
        self.assertTrue(partner.is_spouse())
        self.assertFalse(partner.is_dependent())

    def test_member_with_no_income(self):
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=20)
        self.assertTrue(adult_child.is_dependent())

    def test_two_qualifying_relatives_in_same_household(self):
        """Adult child ($0) and elderly parent ($4k SS) are both qualifying relatives in the same household."""
        adult_child = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=22, student=False)
        elderly_parent = HouseholdMember.objects.create(screen=self.screen, relationship="parent", age=72)
        self._add_yearly_income(elderly_parent, 4_000, income_type="sSRetirement")

        self.assertTrue(adult_child.is_dependent())
        self.assertTrue(elderly_parent.is_dependent())

    # MFB-307 regression

    def test_mfb_307_texas_family(self):
        """The bug scenario: 19yo with $0 income should stay in the main tax unit."""
        spouse = HouseholdMember.objects.create(screen=self.screen, relationship="spouse", age=39)
        child19 = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=19, student=False)
        child7 = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=7)

        self._add_yearly_income(self.head, 43_800)
        self._add_yearly_income(spouse, 18_000)

        self.assertTrue(child19.is_dependent())
        self.assertTrue(child7.is_dependent())

        dependents = [m for m in HouseholdMember.objects.filter(screen=self.screen) if m.is_dependent()]
        self.assertEqual(len(dependents), 2)

    # Other relatives and non-relatives

    def test_aunt_with_low_income(self):
        aunt = HouseholdMember.objects.create(screen=self.screen, relationship="relatedOther", age=50)
        self._add_yearly_income(aunt, 2_000)
        self.assertTrue(aunt.is_dependent())

    def test_grandchild_low_income(self):
        grandchild = HouseholdMember.objects.create(screen=self.screen, relationship="grandChild", age=20)
        self._add_yearly_income(grandchild, 1_000)
        self.assertTrue(grandchild.is_dependent())

    def test_two_student_roommates_do_not_trigger_path_1(self):
        """Regression: unrelated student roommate must not be classified as dependent."""
        _, roommate = self._setup_path_1_household("roommate")

        self.assertFalse(roommate.is_dependent())
        self.assertFalse(roommate.is_in_tax_unit())

    def test_low_income_unrelated_housemate_does_not_trigger_path_2(self):
        """Regression: low-income unrelated member must not pass qualifying-relative path."""
        roommate = self._setup_path_2_household("roommate", income=1_000)

        self.assertFalse(roommate.is_dependent())
        self.assertFalse(roommate.is_in_tax_unit())

    def test_disabled_adult_above_qualifying_relative_threshold_still_dependent(self):
        self._add_yearly_income(self.head, 100_000)
        disabled_adult = HouseholdMember.objects.create(screen=self.screen, relationship="child", age=30, disabled=True)
        self._add_yearly_income(disabled_adult, 8_000)
        self.assertTrue(disabled_adult.is_dependent())
