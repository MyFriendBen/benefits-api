"""
Unit tests for MaMbta MBTA service area filtering.
"""

from django.test import TestCase
from unittest.mock import Mock, MagicMock

from programs.programs.ma.pe.member import MaMbta


class TestMaMbta(TestCase):
    """Tests for MaMbta geographic eligibility filtering."""

    def _create_calculator(self, county):
        mock_screen = Mock()
        mock_screen.county = county
        calculator = MaMbta(mock_screen, Mock(), Mock())
        calculator._sim = MagicMock()
        return calculator

    def test_member_value_returns_amount_for_eligible_city(self):
        calculator = self._create_calculator("Boston")
        calculator.get_member_dependency_value = Mock(return_value=True)

        member = Mock()
        member.id = 1

        self.assertEqual(calculator.member_value(member), MaMbta.amount)

    def test_member_value_returns_zero_for_ineligible_city(self):
        calculator = self._create_calculator("Springfield")
        calculator.get_member_dependency_value = Mock(return_value=True)

        member = Mock()
        member.id = 1

        self.assertEqual(calculator.member_value(member), 0)

    def test_ineligible_city_short_circuits_before_pe_call(self):
        calculator = self._create_calculator("Pittsfield")
        calculator.get_member_dependency_value = Mock(return_value=True)

        member = Mock()
        member.id = 1

        calculator.member_value(member)
        calculator.get_member_dependency_value.assert_not_called()

    def test_member_value_returns_zero_when_pe_ineligible(self):
        calculator = self._create_calculator("Cambridge")
        calculator.get_member_dependency_value = Mock(return_value=False)

        member = Mock()
        member.id = 1

        self.assertEqual(calculator.member_value(member), 0)
