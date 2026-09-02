"""TX tests."""

from unittest.mock import MagicMock
from programs.programs.cross_white_label.medicaid.base import Medicaid
from unittest.mock import Mock
from django.test import TestCase
from programs.programs.cross_white_label.medicaid.emergency.tx import TxEmergencyMedicaid
from programs.programs.cross_white_label.medicaid.for_parents_and_caretakers.tx import TxMedicaidForParentsAndCaretakers
from programs.framework.pe_dependencies.household import TxStateCodeDependency
from programs.framework.pe_dependencies import household


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
