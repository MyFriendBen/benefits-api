"""Recovered from pe/pe/tests."""

from unittest.mock import Mock, MagicMock
from django.test import TestCase
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import member as member_deps
from programs.framework.pe_dependencies.household import KsStateCodeDependency
from programs.framework.pe_dependencies.member import AgeDependency, PregnancyDependency, Chip
from programs.framework.pe_dependencies.tax import KsChipPremium
from programs.programs.cross_white_label.medicaid.ks import KsKanCare
from programs.programs.cross_white_label.medicaid.chip.ks import KsChip
from programs.framework.pe_dependencies import member


class TestKsChip(TestCase):
    """Tests for the KsChip calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """KsChip exists and follows the member-level calculator pattern."""
        self.assertTrue(issubclass(KsChip, PolicyEngineMembersCalculator))
        self.assertIsNotNone(KsChip.pe_inputs)
        self.assertGreater(len(KsChip.pe_inputs), 0)

    def test_pe_name_is_chip(self):
        """KsChip reads PolicyEngine's federal `chip` output."""
        self.assertEqual(KsChip.pe_name, "chip")

    def test_pe_inputs_includes_age_dependency(self):
        """CHIP eligibility is age-gated (under 19)."""
        self.assertIn(AgeDependency, KsChip.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_pregnancy_dependency(self):
        """PregnancyDependency mirrors the federal Chip inputs."""
        self.assertIn(PregnancyDependency, KsChip.pe_inputs)
        self.assertEqual(PregnancyDependency.field, "is_pregnant")

    def test_pe_inputs_match_ks_medicaid_inputs(self):
        """CHIP gates on ~is_medicaid_eligible, and every program on a screen shares one
        PolicyEngine simulation, so CHIP must send the exact same KS Medicaid inputs as
        KsKanCare — otherwise the shared medicaid computation would be inconsistent."""
        self.assertEqual(KsChip.pe_inputs, KsKanCare.pe_inputs)

    def test_pe_inputs_includes_all_ks_medicaid_inputs(self):
        """CHIP reuses KsKanCare.pe_inputs verbatim, so it carries every KS Medicaid input."""
        for kancare_input in KsKanCare.pe_inputs:
            self.assertIn(kancare_input, KsChip.pe_inputs)

    def test_pe_inputs_includes_ssi_countable_resources(self):
        """Inherited via KsKanCare.pe_inputs; CHIP applies no resource test of its own."""
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsChip.pe_inputs)

    def test_pe_inputs_includes_ks_state_code_dependency(self):
        """KsStateCodeDependency sets state_code=KS so PE applies the KS income limit (2.55)."""
        self.assertIn(KsStateCodeDependency, KsChip.pe_inputs)
        self.assertEqual(KsStateCodeDependency.state, "KS")
        self.assertEqual(KsStateCodeDependency.field, "state_code")

    def test_pe_outputs_includes_chip_dependency(self):
        """The per-child coverage value comes from PE's `chip` output."""
        self.assertIn(Chip, KsChip.pe_outputs)
        self.assertEqual(Chip.field, "chip")

    def test_pe_outputs_includes_ks_chip_premium_dependency(self):
        """KS additionally surfaces the tax-unit-level `ks_chip_premium`."""
        self.assertIn(KsChipPremium, KsChip.pe_outputs)
        self.assertEqual(KsChipPremium.field, "ks_chip_premium")
        self.assertEqual(KsChipPremium.unit, "tax_units")

    def test_member_value_returns_pe_value_when_member_has_no_insurance(self):
        """An uninsured child receives the full PE-calculated coverage value."""
        calculator = KsChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        pe_value = 1896
        calculator.get_member_variable = Mock(return_value=pe_value)

        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=True)

        result = calculator.member_value(member)

        self.assertEqual(result, pe_value)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_zero_when_member_has_insurance(self):
        """A child with any other coverage is zeroed out (uninsured-only rule)."""
        calculator = KsChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        pe_value = 1896
        calculator.get_member_variable = Mock(return_value=pe_value)

        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=False)

        result = calculator.member_value(member)

        self.assertEqual(result, 0)
        member.has_insurance_types.assert_called_once_with(("none",))
