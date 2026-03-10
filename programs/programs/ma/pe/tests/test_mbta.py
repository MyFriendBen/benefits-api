"""
Unit tests for MaMbta PolicyEngine calculator class.

These tests verify MA-specific calculator logic for MBTA Reduced Fare Program including:
- MaMbta calculator registration and configuration
- MBTA service area (city) filtering behavior
- PolicyEngine dependency integration
"""

from django.test import TestCase
from unittest.mock import Mock, MagicMock

from programs.programs.policyengine.calculators.base import PolicyEngineMembersCalculator
from programs.programs.policyengine.calculators.dependencies import member as member_deps
from programs.programs.ma.pe import ma_pe_calculators
from programs.programs.ma.pe.member import MaMbta


class TestMaMbta(TestCase):
    """Tests for MaMbta calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """Test that MaMbta inherits from PolicyEngineMembersCalculator."""
        self.assertTrue(issubclass(MaMbta, PolicyEngineMembersCalculator))

    def test_is_registered_in_ma_pe_calculators(self):
        """Test that MA MBTA is registered in the calculators dictionary."""
        self.assertIn("ma_mbta", ma_pe_calculators)
        self.assertEqual(ma_pe_calculators["ma_mbta"], MaMbta)

    def test_eligible_cities_is_defined(self):
        """Test that MaMbta has eligible_cities defined as a frozenset."""
        self.assertIsInstance(MaMbta.eligible_cities, frozenset)
        # 177 MBTA Communities Act municipalities + Boston = 178
        self.assertEqual(len(MaMbta.eligible_cities), 178)

    def test_eligible_cities_includes_boston(self):
        """Test that Boston is included in the MBTA service area."""
        self.assertIn("Boston", MaMbta.eligible_cities)

    def test_eligible_cities_includes_manchester_by_the_sea(self):
        """
        Test that Manchester By The Sea uses the codebase naming convention.

        The official MBTA list uses 'Manchester' but the codebase's
        counties_by_zipcode uses 'Manchester By The Sea'.
        """
        self.assertIn("Manchester By The Sea", MaMbta.eligible_cities)
        self.assertNotIn("Manchester", MaMbta.eligible_cities)

    def test_eligible_cities_excludes_western_ma(self):
        """Test that cities outside the MBTA service area are excluded."""
        non_mbta_cities = ["Springfield", "Pittsfield", "Northampton", "Amherst", "Greenfield"]
        for city in non_mbta_cities:
            with self.subTest(city=city):
                self.assertNotIn(city, MaMbta.eligible_cities)

    def test_amount(self):
        """Test that the MBTA benefit amount is $60/month ($720/year)."""
        self.assertEqual(MaMbta.amount, 720)

    def test_pe_inputs_includes_age_dependency(self):
        """Test that MaMbta includes AgeDependency in pe_inputs."""
        self.assertIn(member_deps.AgeDependency, MaMbta.pe_inputs)

    def test_pe_inputs_includes_is_disabled_dependency(self):
        """Test that MaMbta includes IsDisabledDependency in pe_inputs."""
        self.assertIn(member_deps.IsDisabledDependency, MaMbta.pe_inputs)

    def test_pe_outputs_includes_mbta_dependencies(self):
        """Test that MaMbta has all required MBTA pe_outputs."""
        self.assertIn(member_deps.MaMbtaProgramsEligible, MaMbta.pe_outputs)
        self.assertIn(member_deps.MaMbtaAgeEligible, MaMbta.pe_outputs)
        self.assertIn(member_deps.MaSeniorCharlieCardEligible, MaMbta.pe_outputs)
        self.assertIn(member_deps.MaTapCharlieCardEligible, MaMbta.pe_outputs)

    def _create_calculator(self, county):
        """Helper to create a mock MaMbta calculator instance."""
        mock_screen = Mock()
        mock_screen.county = county
        calculator = MaMbta(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        return calculator

    def _mock_pe_eligible(self, calculator):
        """Helper to mock PolicyEngine returning eligible for all MBTA checks."""
        calculator.get_member_dependency_value = Mock(return_value=True)

    def _mock_pe_ineligible(self, calculator):
        """Helper to mock PolicyEngine returning ineligible for all MBTA checks."""
        calculator.get_member_dependency_value = Mock(return_value=False)

    def test_member_value_returns_amount_when_in_eligible_city_and_pe_eligible(self):
        """Test that member_value returns benefit amount for eligible city + eligible member."""
        calculator = self._create_calculator("Boston")
        self._mock_pe_eligible(calculator)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)
        self.assertEqual(result, MaMbta.amount)

    def test_member_value_returns_zero_when_not_in_eligible_city(self):
        """Test that member_value returns 0 for a city outside the MBTA service area."""
        calculator = self._create_calculator("Springfield")
        self._mock_pe_eligible(calculator)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)
        self.assertEqual(result, 0)

    def test_member_value_city_check_happens_before_pe_call(self):
        """
        Test that city eligibility check occurs before calling PolicyEngine.

        The city check should short-circuit and not make the PE dependency calls
        if the city is not eligible.
        """
        calculator = self._create_calculator("Pittsfield")
        calculator.get_member_dependency_value = Mock(return_value=True)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)

        self.assertEqual(result, 0)
        calculator.get_member_dependency_value.assert_not_called()

    def test_member_value_returns_zero_when_pe_ineligible_in_eligible_city(self):
        """Test that member_value returns 0 when PE says not eligible, even in MBTA city."""
        calculator = self._create_calculator("Cambridge")
        self._mock_pe_ineligible(calculator)

        member = Mock()
        member.id = 1

        result = calculator.member_value(member)
        self.assertEqual(result, 0)

    def test_member_value_with_sample_eligible_cities(self):
        """Test that member_value returns benefit amount for various MBTA cities."""
        sample_cities = ["Boston", "Cambridge", "Somerville", "Brookline", "Worcester", "Lowell", "Fall River"]

        for city in sample_cities:
            with self.subTest(city=city):
                calculator = self._create_calculator(city)
                self._mock_pe_eligible(calculator)

                member = Mock()
                member.id = 1

                result = calculator.member_value(member)
                self.assertEqual(result, MaMbta.amount)

    def test_member_value_with_sample_ineligible_cities(self):
        """Test that member_value returns 0 for various non-MBTA cities."""
        non_mbta_cities = ["Springfield", "Pittsfield", "Northampton", "Amherst", "Greenfield", "Holyoke"]

        for city in non_mbta_cities:
            with self.subTest(city=city):
                calculator = self._create_calculator(city)
                self._mock_pe_eligible(calculator)

                member = Mock()
                member.id = 1

                result = calculator.member_value(member)
                self.assertEqual(result, 0)
