"""
Unit tests for federal Medicaid calculator eligibility logic.

These tests verify that:
1. Seniors (65+) and disabled individuals are correctly routed through the
   aged/disabled pathway and not the ACA expansion pathway
2. Non-senior, non-disabled members are routed through the appropriate
   Medicaid category (ADULT, PARENT, PREGNANT, INFANT, CHILD, etc.)

ACA Medicaid expansion (138% FPL) only applies to adults under 65.
Seniors must qualify through the aged/disabled pathway which uses
state-specific FPL thresholds (typically 74-100%).
"""

from django.test import TestCase
from unittest.mock import Mock, MagicMock

from programs.programs.federal.pe.member import Medicaid
from programs.programs.policyengine.calculators.dependencies import member as member_dependency


class TestMedicaidSeniorEligibility(TestCase):
    """Tests for Medicaid calculator senior eligibility routing."""

    def _create_calculator_with_mocks(self):
        """Helper to create a Medicaid calculator with mocked dependencies."""
        calculator = Medicaid(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock()
        calculator.get_member_dependency_value = Mock()
        return calculator

    def _create_member(self, age, is_disabled=False):
        """Helper to create a mock member."""
        member = Mock()
        member.id = 1
        member.age = age
        member.has_disability = Mock(return_value=is_disabled)
        return member

    def test_senior_who_qualifies_via_aged_pathway_returns_aged_category(self):
        """
        Test that a senior (65+) who qualifies via the aged/disabled pathway
        returns the AGED category value.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"AGED": 474, "ADULT": 474}

        # Senior qualifies via aged/disabled pathway
        calculator.get_member_dependency_value.return_value = True

        member = self._create_member(age=71)

        result = calculator.member_value(member)

        # Should return AGED category * 12
        self.assertEqual(result, 474 * 12)

        # Should have checked the aged/disabled pathway
        calculator.get_member_dependency_value.assert_called_once_with(
            member_dependency.MedicaidSeniorOrDisabled, 1
        )

    def test_senior_who_fails_aged_pathway_returns_zero(self):
        """
        Test that a senior (65+) who fails the aged/disabled pathway
        returns 0 and does NOT fall through to ACA expansion.

        This is the key bug fix - previously seniors could fall through
        to the 138% FPL ACA adult pathway.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"AGED": 474, "ADULT": 474}

        # Senior fails aged/disabled pathway (e.g., income > 100% FPL)
        calculator.get_member_dependency_value.return_value = False

        # Even if regular medicaid would return positive (138% FPL)
        calculator.get_member_variable.return_value = 500

        member = self._create_member(age=71)

        result = calculator.member_value(member)

        # Should return 0, NOT fall through to ACA adult pathway
        self.assertEqual(result, 0)

        # Should NOT have called get_member_variable (no ACA fallback)
        calculator.get_member_variable.assert_not_called()

    def test_senior_at_age_65_boundary_uses_aged_pathway(self):
        """
        Test that exactly 65 years old uses the aged/disabled pathway.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"AGED": 474, "ADULT": 474}

        calculator.get_member_dependency_value.return_value = True

        member = self._create_member(age=65)

        result = calculator.member_value(member)

        # Should use AGED pathway
        self.assertEqual(result, 474 * 12)
        calculator.get_member_dependency_value.assert_called_once()

    def test_adult_age_64_uses_aca_pathway_not_aged(self):
        """
        Test that 64-year-old uses ACA expansion pathway, not aged pathway.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"AGED": 474, "ADULT": 474}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "ADULT"

        member = self._create_member(age=64)

        result = calculator.member_value(member)

        # Should return ADULT category * 12
        self.assertEqual(result, 474 * 12)

        # Should have called get_member_variable for ACA check
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_with_none_age_uses_aca_pathway(self):
        """
        Test that members with None age are treated as non-seniors
        and use the ACA expansion pathway.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"ADULT": 474}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "ADULT"

        member = self._create_member(age=None)

        result = calculator.member_value(member)

        # Should use ACA pathway (not crash on None comparison)
        self.assertEqual(result, 474 * 12)
        calculator.get_member_variable.assert_called_once()


class TestMedicaidDisabledEligibility(TestCase):
    """Tests for Medicaid calculator disabled eligibility routing."""

    def _create_calculator_with_mocks(self):
        calculator = Medicaid(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock()
        calculator.get_member_dependency_value = Mock()
        return calculator

    def _create_member(self, age, is_disabled=False):
        member = Mock()
        member.id = 1
        member.age = age
        member.has_disability = Mock(return_value=is_disabled)
        return member

    def test_disabled_adult_uses_disabled_pathway(self):
        """
        Test that disabled adults (any age under 65) use the aged/disabled pathway.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"DISABLED": 474, "ADULT": 474}

        calculator.get_member_dependency_value.return_value = True

        member = self._create_member(age=45, is_disabled=True)

        result = calculator.member_value(member)

        # Should return DISABLED category * 12
        self.assertEqual(result, 474 * 12)

    def test_disabled_adult_who_fails_disabled_pathway_returns_zero(self):
        """
        Test that disabled adults who fail the aged/disabled pathway
        return 0 and do NOT fall through to ACA expansion.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"DISABLED": 474, "ADULT": 474}

        # Disabled person fails aged/disabled pathway
        calculator.get_member_dependency_value.return_value = False

        # Even if ACA would pass
        calculator.get_member_variable.return_value = 500

        member = self._create_member(age=45, is_disabled=True)

        result = calculator.member_value(member)

        # Should return 0, NOT fall through
        self.assertEqual(result, 0)
        calculator.get_member_variable.assert_not_called()

    def test_disabled_senior_returns_disabled_not_aged(self):
        """
        Test that a disabled senior (65+) returns DISABLED category,
        not AGED category. Disability takes priority.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"DISABLED": 500, "AGED": 474}

        calculator.get_member_dependency_value.return_value = True

        member = Mock()
        member.id = 1
        member.age = 70
        member.has_disability = Mock(return_value=True)

        result = calculator.member_value(member)

        # Should return DISABLED (500 * 12), not AGED (474 * 12)
        self.assertEqual(result, 500 * 12)

    def test_disabled_child_uses_disabled_pathway(self):
        """
        Test that a disabled child uses the aged/disabled pathway.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"DISABLED": 474, "OLDER_CHILD": 200}

        calculator.get_member_dependency_value.return_value = True

        member = self._create_member(age=10, is_disabled=True)

        result = calculator.member_value(member)

        # Should return DISABLED category * 12
        self.assertEqual(result, 474 * 12)


class TestMedicaidAdultEligibility(TestCase):
    """Tests for Medicaid calculator adult (non-senior, non-disabled) eligibility."""

    def _create_calculator_with_mocks(self):
        calculator = Medicaid(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock()
        calculator.get_member_dependency_value = Mock()
        return calculator

    def _create_member(self, age, is_disabled=False):
        member = Mock()
        member.id = 1
        member.age = age
        member.has_disability = Mock(return_value=is_disabled)
        return member

    def test_adult_who_qualifies_returns_adult_category(self):
        """
        Test that an adult who qualifies via ACA expansion returns ADULT category.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"ADULT": 474}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "ADULT"

        member = self._create_member(age=35)

        result = calculator.member_value(member)

        self.assertEqual(result, 474 * 12)

    def test_adult_who_fails_aca_returns_zero(self):
        """
        Test that adults who fail ACA expansion (income > 138% FPL) return 0.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"ADULT": 474}

        # ACA expansion returns 0 (income > 138% FPL)
        calculator.get_member_variable.return_value = 0

        member = self._create_member(age=50)

        result = calculator.member_value(member)

        self.assertEqual(result, 0)


class TestMedicaidParentEligibility(TestCase):
    """Tests for Medicaid calculator parent/caretaker eligibility."""

    def _create_calculator_with_mocks(self):
        calculator = Medicaid(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock()
        calculator.get_member_dependency_value = Mock()
        return calculator

    def _create_member(self, age, is_disabled=False):
        member = Mock()
        member.id = 1
        member.age = age
        member.has_disability = Mock(return_value=is_disabled)
        return member

    def test_parent_who_qualifies_returns_parent_category(self):
        """
        Test that a parent/caretaker who qualifies returns PARENT category value.
        PolicyEngine determines PARENT category based on having qualifying children.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"PARENT": 474, "ADULT": 400}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "PARENT"

        member = self._create_member(age=35)

        result = calculator.member_value(member)

        # Should return PARENT category * 12
        self.assertEqual(result, 474 * 12)

    def test_parent_category_has_different_value_than_adult(self):
        """
        Test that PARENT and ADULT categories can have different values.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"PARENT": 500, "ADULT": 400}

        calculator.get_member_variable.return_value = 100
        calculator.get_member_dependency_value.return_value = "PARENT"

        member = self._create_member(age=30)

        result = calculator.member_value(member)

        self.assertEqual(result, 500 * 12)


class TestMedicaidPregnantEligibility(TestCase):
    """Tests for Medicaid calculator pregnant eligibility."""

    def _create_calculator_with_mocks(self):
        calculator = Medicaid(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock()
        calculator.get_member_dependency_value = Mock()
        return calculator

    def _create_member(self, age, is_disabled=False):
        member = Mock()
        member.id = 1
        member.age = age
        member.has_disability = Mock(return_value=is_disabled)
        return member

    def test_pregnant_member_who_qualifies_returns_pregnant_category(self):
        """
        Test that a pregnant member who qualifies returns PREGNANT category value.
        PolicyEngine uses higher FPL thresholds for pregnant members (e.g., 213% for IL).
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"PREGNANT": 474, "ADULT": 400}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "PREGNANT"

        member = self._create_member(age=28)

        result = calculator.member_value(member)

        self.assertEqual(result, 474 * 12)

    def test_pregnant_senior_uses_aged_pathway_not_pregnant(self):
        """
        Test that a pregnant senior (65+) still uses aged/disabled pathway.
        Age routing takes precedence over pregnancy status.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"AGED": 474, "PREGNANT": 500}

        calculator.get_member_dependency_value.return_value = True

        member = self._create_member(age=66)

        result = calculator.member_value(member)

        # Should return AGED, not PREGNANT
        self.assertEqual(result, 474 * 12)


class TestMedicaidChildEligibility(TestCase):
    """Tests for Medicaid calculator child eligibility."""

    def _create_calculator_with_mocks(self):
        calculator = Medicaid(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock()
        calculator.get_member_dependency_value = Mock()
        return calculator

    def _create_member(self, age, is_disabled=False):
        member = Mock()
        member.id = 1
        member.age = age
        member.has_disability = Mock(return_value=is_disabled)
        return member

    def test_infant_who_qualifies_returns_infant_category(self):
        """
        Test that an infant who qualifies returns INFANT category value.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"INFANT": 0, "YOUNG_CHILD": 0}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "INFANT"

        member = self._create_member(age=0)

        result = calculator.member_value(member)

        self.assertEqual(result, 0 * 12)

    def test_young_child_who_qualifies_returns_young_child_category(self):
        """
        Test that a young child who qualifies returns YOUNG_CHILD category value.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"YOUNG_CHILD": 200}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "YOUNG_CHILD"

        member = self._create_member(age=3)

        result = calculator.member_value(member)

        self.assertEqual(result, 200 * 12)

    def test_older_child_who_qualifies_returns_older_child_category(self):
        """
        Test that an older child who qualifies returns OLDER_CHILD category value.
        PolicyEngine uses higher FPL thresholds for children (e.g., 318% for IL).
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"OLDER_CHILD": 284}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "OLDER_CHILD"

        member = self._create_member(age=12)

        result = calculator.member_value(member)

        self.assertEqual(result, 284 * 12)

    def test_child_who_fails_income_returns_zero(self):
        """
        Test that a child who fails the income test returns 0.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"OLDER_CHILD": 284}

        calculator.get_member_variable.return_value = 0

        member = self._create_member(age=15)

        result = calculator.member_value(member)

        self.assertEqual(result, 0)


class TestMedicaidYoungAdultEligibility(TestCase):
    """Tests for Medicaid calculator young adult eligibility."""

    def _create_calculator_with_mocks(self):
        calculator = Medicaid(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock()
        calculator.get_member_dependency_value = Mock()
        return calculator

    def _create_member(self, age, is_disabled=False):
        member = Mock()
        member.id = 1
        member.age = age
        member.has_disability = Mock(return_value=is_disabled)
        return member

    def test_young_adult_who_qualifies_returns_young_adult_category(self):
        """
        Test that a young adult (typically 19-20) who qualifies returns YOUNG_ADULT category.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"YOUNG_ADULT": 300, "ADULT": 474}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "YOUNG_ADULT"

        member = self._create_member(age=19)

        result = calculator.member_value(member)

        self.assertEqual(result, 300 * 12)


class TestMedicaidSSIRecipientEligibility(TestCase):
    """Tests for Medicaid calculator SSI recipient eligibility."""

    def _create_calculator_with_mocks(self):
        calculator = Medicaid(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock()
        calculator.get_member_dependency_value = Mock()
        return calculator

    def _create_member(self, age, is_disabled=False):
        member = Mock()
        member.id = 1
        member.age = age
        member.has_disability = Mock(return_value=is_disabled)
        return member

    def test_ssi_recipient_returns_ssi_recipient_category(self):
        """
        Test that an SSI recipient returns SSI_RECIPIENT category value.
        SSI recipients are categorically eligible for Medicaid.
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"SSI_RECIPIENT": 474, "ADULT": 400}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "SSI_RECIPIENT"

        member = self._create_member(age=55)

        result = calculator.member_value(member)

        self.assertEqual(result, 474 * 12)


class TestMedicaidNoneCategory(TestCase):
    """Tests for Medicaid calculator when no category applies."""

    def _create_calculator_with_mocks(self):
        calculator = Medicaid(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.get_member_variable = Mock()
        calculator.get_member_dependency_value = Mock()
        return calculator

    def _create_member(self, age, is_disabled=False):
        member = Mock()
        member.id = 1
        member.age = age
        member.has_disability = Mock(return_value=is_disabled)
        return member

    def test_none_category_returns_zero(self):
        """
        Test that NONE category returns 0 (no Medicaid eligibility).
        """
        calculator = self._create_calculator_with_mocks()
        calculator.medicaid_categories = {"NONE": 0, "ADULT": 474}

        calculator.get_member_variable.return_value = 500
        calculator.get_member_dependency_value.return_value = "NONE"

        member = self._create_member(age=40)

        result = calculator.member_value(member)

        self.assertEqual(result, 0 * 12)
