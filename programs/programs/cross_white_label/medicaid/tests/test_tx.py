"""TX Medicaid tests."""

from unittest.mock import MagicMock
from programs.programs.cross_white_label.medicaid.base import Medicaid
from unittest.mock import Mock
from django.test import TestCase
from programs.programs.cross_white_label.medicaid.tx.emergency_medicaid.calculator import TxEmergencyMedicaid
from programs.programs.cross_white_label.medicaid.tx.for_children.calculator import TxMedicaidForChildren
from programs.programs.cross_white_label.medicaid.tx.for_parents_and_caretakers.calculator import (
    TxMedicaidForParentsAndCaretakers,
)
from programs.programs.cross_white_label.medicaid.tx.for_pregnant_women.calculator import TxMedicaidForPregnantWomen
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household
from programs.framework.pe_dependencies import member


class TestTxEmergencyMedicaid(TestCase):
    """Tests for TxEmergencyMedicaid calculator class."""

    def test_exists_and_is_subclass_of_medicaid(self):
        """
        Test that TxEmergencyMedicaid calculator class exists and is a subclass of Medicaid.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxEmergencyMedicaid is a subclass of Medicaid
        self.assertTrue(issubclass(TxEmergencyMedicaid, Medicaid))

        # Verify it has the expected properties
        self.assertEqual(TxEmergencyMedicaid.pe_name, "medicaid")
        self.assertIsNotNone(TxEmergencyMedicaid.pe_inputs)
        self.assertGreater(len(TxEmergencyMedicaid.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxEmergencyMedicaid has all expected pe_inputs from parent and TX-specific.

        TxEmergencyMedicaid should inherit all inputs from parent Medicaid class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxEmergencyMedicaid should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxEmergencyMedicaid.pe_inputs), len(Medicaid.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxEmergencyMedicaid.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, TxEmergencyMedicaid.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Emergency Medicaid inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxEmergencyMedicaid.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxEmergencyMedicaid has the same pe_outputs as parent Medicaid class."""
        # TxEmergencyMedicaid should use the same outputs as parent
        self.assertEqual(TxEmergencyMedicaid.pe_outputs, Medicaid.pe_outputs)


class TestTxMedicaidForChildren(TestCase):
    """Tests for TxMedicaidForChildren calculator class."""

    def test_exists_and_is_subclass_of_medicaid(self):
        """
        Test that TxMedicaidForChildren calculator class exists and is a subclass of Medicaid.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxMedicaidForChildren is a subclass of Medicaid
        self.assertTrue(issubclass(TxMedicaidForChildren, Medicaid))

        # Verify it has the expected properties
        self.assertEqual(TxMedicaidForChildren.pe_name, "medicaid")
        self.assertIsNotNone(TxMedicaidForChildren.pe_inputs)
        self.assertGreater(len(TxMedicaidForChildren.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxMedicaidForChildren has all expected pe_inputs from parent and TX-specific.

        TxMedicaidForChildren should inherit all inputs from parent Medicaid class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxMedicaidForChildren should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxMedicaidForChildren.pe_inputs), len(Medicaid.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxMedicaidForChildren.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, TxMedicaidForChildren.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Medicaid inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxMedicaidForChildren.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxMedicaidForChildren has the same pe_outputs as parent Medicaid class."""
        # TxMedicaidForChildren should use the same outputs as parent
        self.assertEqual(TxMedicaidForChildren.pe_outputs, Medicaid.pe_outputs)

    def test_member_value_returns_zero_for_adults_age_19_or_older(self):
        """
        Test that member_value returns 0 for members aged 19 or older.

        TX Medicaid for Children is only for children under 19.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the parent's member_value method
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock member aged 19
        member = Mock()
        member.id = 1
        member.age = 19
        member.has_insurance_types = Mock(return_value=True)
        member.has_disability = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (too old)
        self.assertEqual(result, 0)

    def test_member_value_returns_zero_for_children_with_insurance(self):
        """
        Test that member_value returns 0 for children who have other insurance.

        TX Medicaid for Children requires that children do not have other health insurance.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock member under 19 with insurance
        member = Mock()
        member.id = 1
        member.age = 10
        member.has_insurance_types = Mock(return_value=False)  # has_insurance_types(("none",)) returns False
        member.has_disability = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (has insurance)
        self.assertEqual(result, 0)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_pe_value_for_eligible_children(self):
        """
        Test that member_value returns PolicyEngine value for eligible children.

        When a child is under 19 and has no insurance, the PolicyEngine-calculated
        Medicaid value should be returned directly.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 250
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member under 19 without insurance
        member = Mock()
        member.id = 1
        member.age = 12
        member.has_insurance_types = Mock(return_value=True)  # has_insurance_types(("none",)) returns True

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value directly
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_age_boundary_18_is_eligible(self):
        """
        Test that 18-year-olds are eligible for TX Medicaid for Children.

        The program covers children 18 and under, so 18 should be eligible.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 300
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member aged 18 without insurance
        member = Mock()
        member.id = 1
        member.age = 18
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value (18 is eligible)
        self.assertEqual(result, pe_value)

    def test_member_value_checks_age_before_insurance(self):
        """
        Test that age check happens before insurance check for efficiency.

        If a member is too old, we shouldn't need to check their insurance status.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Create a mock member aged 25
        member = Mock()
        member.id = 1
        member.age = 25
        member.has_insurance_types = Mock()  # Should not be called

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0
        self.assertEqual(result, 0)

        # Insurance check should not be called since age check fails first
        member.has_insurance_types.assert_not_called()

    def test_member_value_with_infant(self):
        """
        Test that member_value works correctly for infants (age 0).

        Infants should be eligible if they have no other insurance.
        """
        # Create a mock TxMedicaidForChildren calculator instance
        calculator = TxMedicaidForChildren(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 400
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock infant without insurance
        member = Mock()
        member.id = 1
        member.age = 0
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value (infant is eligible)
        self.assertEqual(result, pe_value)


class TestTxMedicaidForParentsAndCaretakers(TestCase):
    """Tests for TxMedicaidForParentsAndCaretakers calculator class."""

    def test_exists_and_is_subclass_of_medicaid(self):
        """
        Test that TxMedicaidForParentsAndCaretakers calculator class exists and is a subclass of Medicaid.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxMedicaidForParentsAndCaretakers is a subclass of Medicaid
        self.assertTrue(issubclass(TxMedicaidForParentsAndCaretakers, Medicaid))

        # Verify it has the expected properties
        self.assertEqual(TxMedicaidForParentsAndCaretakers.pe_name, "medicaid")
        self.assertIsNotNone(TxMedicaidForParentsAndCaretakers.pe_inputs)
        self.assertGreater(len(TxMedicaidForParentsAndCaretakers.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxMedicaidForParentsAndCaretakers has all expected pe_inputs from parent and TX-specific.

        TxMedicaidForParentsAndCaretakers should inherit all inputs from parent Medicaid class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxMedicaidForParentsAndCaretakers should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxMedicaidForParentsAndCaretakers.pe_inputs), len(Medicaid.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxMedicaidForParentsAndCaretakers.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, TxMedicaidForParentsAndCaretakers.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Medicaid for Parents inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxMedicaidForParentsAndCaretakers.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxMedicaidForParentsAndCaretakers has the same pe_outputs as parent Medicaid class."""
        # TxMedicaidForParentsAndCaretakers should use the same outputs as parent
        self.assertEqual(TxMedicaidForParentsAndCaretakers.pe_outputs, Medicaid.pe_outputs)

    def test_caretaker_relationships_defined(self):
        """Test that caretaker relationships are properly defined."""
        expected_relationships = [
            "headOfHousehold",
            "spouse",
            "domesticPartner",
            "parent",
            "stepParent",
            "grandParent",
            "sisterOrBrother",
            "stepSisterOrBrother",
            "relatedOther",
        ]

        self.assertEqual(TxMedicaidForParentsAndCaretakers.caretaker_relationships, expected_relationships)

    def test_member_value_returns_zero_for_children_under_19(self):
        """
        Test that member_value returns 0 for members under 19.

        TX Medicaid for Parents and Caretakers is for adults 19 and older.
        """
        # Create a mock calculator instance
        calculator = TxMedicaidForParentsAndCaretakers(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)

        # Create a mock member aged 18
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 18
        member_obj.has_insurance_types = Mock(return_value=True)
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0 (too young)
        self.assertEqual(result, 0)

    def test_member_value_returns_zero_for_adults_with_insurance(self):
        """
        Test that member_value returns 0 for adults who have other health insurance.

        TX Medicaid for Parents and Caretakers requires that adults do not have other insurance.
        """
        # Create a mock calculator instance
        calculator = TxMedicaidForParentsAndCaretakers(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)

        # Create a mock adult with insurance
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 35
        member_obj.has_insurance_types = Mock(return_value=False)  # has_insurance_types(("none",)) returns False
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0 (has insurance)
        self.assertEqual(result, 0)
        member_obj.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_zero_for_non_caretaker_relationship(self):
        """
        Test that member_value returns 0 for adults with non-caretaker relationships.

        Only certain relationships qualify as caretakers (headOfHousehold, spouse, domesticPartner,
        parent, stepParent, grandParent, sisterOrBrother, stepSisterOrBrother, relatedOther).
        """
        # Create a mock calculator instance with screen
        mock_screen = Mock()
        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)

        # Create a mock adult with a non-qualifying relationship (e.g., "other")
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 35
        member_obj.has_insurance_types = Mock(return_value=True)  # No insurance
        member_obj.relationship = "other"  # Not a qualifying relationship

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0 (not a qualifying caretaker relationship)
        self.assertEqual(result, 0)

    def test_member_value_returns_zero_when_no_child_with_medicaid(self):
        """
        Test that member_value returns 0 when household has no child under 19 with Medicaid.

        A qualifying child must be in the household for caretaker eligibility.
        """
        # Create a mock screen with no children
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = []  # No children in household
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)

        # Create a mock adult caretaker
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 35
        member_obj.has_insurance_types = Mock(return_value=True)  # No insurance
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0 (no child with Medicaid in household)
        self.assertEqual(result, 0)

    def test_member_value_returns_pe_value_for_eligible_caretaker(self):
        """
        Test that member_value returns PolicyEngine value for eligible caretakers.

        When an adult is 19+, has no insurance, has a qualifying relationship,
        and household has a child with Medicaid, the PE value should be returned.
        """
        # Create a mock child with Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 10
        mock_child.has_insurance = Mock(return_value=True)  # Child has Medicaid

        # Create a mock screen with the child
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        pe_value = 300
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock eligible adult caretaker
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 35
        member_obj.has_insurance_types = Mock(return_value=True)  # No insurance
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return the PolicyEngine value
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_with(1)

    def test_member_value_eligible_with_child_qualifying_for_medicaid(self):
        """
        Test that caretaker is eligible when child qualifies for Medicaid (PE value > 0).

        Even if child doesn't currently have Medicaid, if they qualify (PE value > 0),
        the caretaker should be eligible.
        """
        # Create a mock child who qualifies for Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 10
        mock_child.has_insurance = Mock(return_value=False)  # Child doesn't have Medicaid yet

        # Create a mock screen with the child
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine values - child qualifies (> 0), adult also qualifies
        calculator.get_member_dependency_value = Mock(return_value=250)  # Child qualifies for Medicaid
        calculator.get_member_variable = Mock(return_value=300)  # Adult's value

        # Create a mock eligible adult caretaker
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 35
        member_obj.has_insurance_types = Mock(return_value=True)  # No insurance
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return the adult's PolicyEngine value
        self.assertEqual(result, 300)

    def test_member_value_age_boundary_19_is_eligible(self):
        """
        Test that 19-year-olds are eligible (minimum age for the program).

        The program covers adults 19 and older.
        """
        # Create a mock child with Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 5
        mock_child.has_insurance = Mock(return_value=True)

        # Create a mock screen
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        pe_value = 350
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock member aged 19
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 19
        member_obj.has_insurance_types = Mock(return_value=True)
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return the PolicyEngine value (19 is eligible)
        self.assertEqual(result, pe_value)

    def test_member_value_checks_age_before_other_conditions(self):
        """
        Test that age check happens first for efficiency.

        If a member is under 19, we shouldn't need to check other conditions.
        """
        # Create a mock calculator instance
        calculator = TxMedicaidForParentsAndCaretakers(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Create a mock member aged 17
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 17
        member_obj.has_insurance_types = Mock()  # Should not be called
        member_obj.relationship = "headOfHousehold"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return 0
        self.assertEqual(result, 0)

        # Insurance check should not be called since age check fails first
        member_obj.has_insurance_types.assert_not_called()

    def test_member_value_with_sibling_relationship(self):
        """
        Test that sibling relationship qualifies as a caretaker.

        From the requirements, siblings are valid caretakers.
        """
        # Create a mock child with Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 10
        mock_child.has_insurance = Mock(return_value=True)

        # Create a mock screen
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        pe_value = 280
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock adult sibling caretaker
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 25
        member_obj.has_insurance_types = Mock(return_value=True)
        member_obj.relationship = "sisterOrBrother"  # Sibling relationship

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return the PolicyEngine value (sibling is eligible caretaker)
        self.assertEqual(result, pe_value)

    def test_member_value_with_grandparent_relationship(self):
        """
        Test that grandparent relationship qualifies as a caretaker.

        From the requirements, grandparents are valid caretakers.
        """
        # Create a mock child with Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 8
        mock_child.has_insurance = Mock(return_value=True)

        # Create a mock screen
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value
        pe_value = 320
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock grandparent caretaker
        member_obj = Mock()
        member_obj.id = 1
        member_obj.age = 65
        member_obj.has_insurance_types = Mock(return_value=True)
        member_obj.relationship = "grandParent"

        # Call member_value
        result = calculator.member_value(member_obj)

        # Should return the PolicyEngine value (grandparent is eligible caretaker)
        self.assertEqual(result, pe_value)

    def test_has_child_with_medicaid_returns_false_for_adult_only_household(self):
        """
        Test _has_child_with_medicaid returns False when household has no children under 19.
        """
        # Create mock adult members only
        mock_adult = Mock()
        mock_adult.id = 2
        mock_adult.age = 35

        # Create a mock screen with adult only
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_adult]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Call _has_child_with_medicaid
        result = calculator._has_child_with_medicaid()

        # Should return False (no children under 19)
        self.assertFalse(result)

    def test_has_child_with_medicaid_returns_true_for_child_with_benefit(self):
        """
        Test _has_child_with_medicaid returns True when child has Medicaid benefit.
        """
        # Create a mock child with Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 10
        mock_child.has_insurance = Mock(return_value=True)

        # Create a mock screen with the child
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Call _has_child_with_medicaid
        result = calculator._has_child_with_medicaid()

        # Should return True
        self.assertTrue(result)
        mock_child.has_insurance.assert_called_once_with("medicaid")

    def test_has_child_with_medicaid_returns_true_for_child_qualifying_via_pe(self):
        """
        Test _has_child_with_medicaid returns True when child qualifies via PolicyEngine value.
        """
        # Create a mock child who qualifies for Medicaid
        mock_child = Mock()
        mock_child.id = 2
        mock_child.age = 12
        mock_child.has_insurance = Mock(return_value=False)  # Doesn't have it yet

        # Create a mock screen with the child
        mock_screen = Mock()
        mock_household_members = MagicMock()
        mock_household_members.all.return_value = [mock_child]
        mock_screen.household_members = mock_household_members

        calculator = TxMedicaidForParentsAndCaretakers(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        calculator.screen = mock_screen

        # Mock PolicyEngine value > 0 (child qualifies)
        calculator.get_member_dependency_value = Mock(return_value=200)

        # Call _has_child_with_medicaid
        result = calculator._has_child_with_medicaid()

        # Should return True
        self.assertTrue(result)
        calculator.get_member_dependency_value.assert_called_once()


class TestTxMedicaidForPregnantWomen(TestCase):
    """Tests for TxMedicaidForPregnantWomen calculator class."""

    def test_exists_and_is_subclass_of_medicaid(self):
        """
        Test that TxMedicaidForPregnantWomen calculator class exists and is a subclass of Medicaid.

        This verifies the calculator has been set up in the codebase.
        """
        # Verify TxMedicaidForPregnantWomen is a subclass of Medicaid
        self.assertTrue(issubclass(TxMedicaidForPregnantWomen, Medicaid))

        # Verify it has the expected properties
        self.assertEqual(TxMedicaidForPregnantWomen.pe_name, "medicaid")
        self.assertIsNotNone(TxMedicaidForPregnantWomen.pe_inputs)
        self.assertGreater(len(TxMedicaidForPregnantWomen.pe_inputs), 0)

    def test_pe_inputs_includes_all_parent_inputs_plus_tx_specific(self):
        """
        Test that TxMedicaidForPregnantWomen has all expected pe_inputs from parent and TX-specific.

        TxMedicaidForPregnantWomen should inherit all inputs from parent Medicaid class plus add
        TX-specific dependencies like TxStateCodeDependency.
        """
        # TxMedicaidForPregnantWomen should have all parent inputs plus TxStateCodeDependency
        self.assertGreater(len(TxMedicaidForPregnantWomen.pe_inputs), len(Medicaid.pe_inputs))

        # Verify TxStateCodeDependency is in the list
        self.assertIn(household.TxStateCodeDependency, TxMedicaidForPregnantWomen.pe_inputs)

        # Verify all parent inputs are present
        for parent_input in Medicaid.pe_inputs:
            self.assertIn(parent_input, TxMedicaidForPregnantWomen.pe_inputs)

    def test_pe_inputs_includes_tx_state_code_dependency(self):
        """
        Test that TxStateCodeDependency is properly added to TX Medicaid inputs.

        This is the key TX-specific dependency that sets state_code="TX" for
        PolicyEngine calculations.
        """
        # Verify TxStateCodeDependency is in pe_inputs
        self.assertIn(TxStateCodeDependency, TxMedicaidForPregnantWomen.pe_inputs)

        # Verify it's configured correctly
        self.assertEqual(TxStateCodeDependency.state, "TX")
        self.assertEqual(TxStateCodeDependency.field, "state_code")

    def test_has_same_pe_outputs_as_parent(self):
        """Test that TxMedicaidForPregnantWomen has the same pe_outputs as parent Medicaid class."""
        # TxMedicaidForPregnantWomen should use the same outputs as parent
        self.assertEqual(TxMedicaidForPregnantWomen.pe_outputs, Medicaid.pe_outputs)

    def test_member_value_returns_zero_for_non_pregnant_members(self):
        """
        Test that member_value returns 0 for members who are not pregnant.

        TX Medicaid for Pregnant Women is only for pregnant individuals.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the parent's member_value method
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock member who is not pregnant
        member = Mock()
        member.id = 1
        member.pregnant = False
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (not pregnant)
        self.assertEqual(result, 0)

    def test_member_value_returns_zero_for_pregnant_members_with_insurance(self):
        """
        Test that member_value returns 0 for pregnant members who have other insurance.

        TX Medicaid for Pregnant Women requires that pregnant persons do not have other health insurance.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        calculator.get_member_variable = Mock(return_value=100)
        calculator.get_member_dependency_value = Mock()

        # Create a mock pregnant member with insurance
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=False)  # has_insurance_types(("none",)) returns False

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (has insurance)
        self.assertEqual(result, 0)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_pe_value_for_eligible_pregnant_women(self):
        """
        Test that member_value returns PolicyEngine value for eligible pregnant women.

        When a member is pregnant and has no insurance, the PolicyEngine-calculated
        Medicaid value should be returned directly.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock PolicyEngine value
        pe_value = 350
        calculator.get_member_variable = Mock(return_value=pe_value)

        # Create a mock pregnant member without insurance
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=True)  # has_insurance_types(("none",)) returns True

        # Call member_value
        result = calculator.member_value(member)

        # Should return the PolicyEngine value directly
        self.assertEqual(result, pe_value)
        calculator.get_member_variable.assert_called_once_with(1)

    def test_member_value_checks_pregnancy_before_insurance(self):
        """
        Test that pregnancy check happens before insurance check for efficiency.

        If a member is not pregnant, we shouldn't need to check their insurance status.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Create a mock non-pregnant member
        member = Mock()
        member.id = 1
        member.pregnant = False
        member.has_insurance_types = Mock()  # Should not be called

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0
        self.assertEqual(result, 0)

        # Insurance check should not be called since pregnancy check fails first
        member.has_insurance_types.assert_not_called()

    def test_member_value_with_zero_pe_value_and_eligible_pregnant_woman(self):
        """
        Test that member_value returns 0 when PolicyEngine returns 0, even for eligible pregnant women.

        If PolicyEngine determines no benefit value, it should be returned as-is
        (the member may not be income-eligible even though they are pregnant and have no insurance).
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock zero PolicyEngine value
        calculator.get_member_variable = Mock(return_value=0)

        # Create a mock pregnant member without insurance
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 (PE says not eligible based on income)
        self.assertEqual(result, 0)

    def test_member_value_with_high_pe_value_but_has_insurance(self):
        """
        Test that insurance eligibility check occurs regardless of PolicyEngine value.

        Even if PolicyEngine returns a high value, the insurance check should still
        determine the final eligibility.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock high PolicyEngine value
        calculator.get_member_variable = Mock(return_value=500)

        # Create a mock pregnant member with insurance (not eligible)
        member = Mock()
        member.id = 1
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=False)

        # Call member_value
        result = calculator.member_value(member)

        # Should return 0 despite high PE value
        self.assertEqual(result, 0)

        # Verify insurance check was performed
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_calls_get_member_variable_with_member_id(self):
        """
        Test that member_value calls get_member_variable with the correct member ID.

        This verifies that the PolicyEngine value is fetched for the right member.
        """
        # Create a mock TxMedicaidForPregnantWomen calculator instance
        calculator = TxMedicaidForPregnantWomen(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        # Mock the get_member_variable method
        calculator.get_member_variable = Mock(return_value=200)

        # Create a mock pregnant member without insurance
        member = Mock()
        member.id = 99
        member.pregnant = True
        member.has_insurance_types = Mock(return_value=True)

        # Call member_value
        calculator.member_value(member)

        # Verify get_member_variable was called with the correct member ID
        calculator.get_member_variable.assert_called_once_with(99)
