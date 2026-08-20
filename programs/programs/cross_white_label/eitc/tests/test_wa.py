"""WA tests."""

from programs.programs.cross_white_label.eitc.base import Eitc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from django.test import TestCase
from programs.programs.cross_white_label.eitc.wa import WaEitc
from programs.framework.pe_dependencies.household import WaStateCodeDependency
from programs.programs.cross_white_label.eitc.wa_wftc import WaWftc
from programs.framework.pe_dependencies import tax as tax_dependency


class TestWaEitc(TestCase):
    """`wa_eitc` reuses the federal Eitc calculator unchanged (same class object).

    The federal EITC reads no state variable, so there is no WA subclass and no
    state code. Contrast `WaWftc` below, which targets the *state*
    `wa_working_families_tax_credit` variable and does need the state code.

    The calculator's own properties are asserted once in
    `programs/programs/federal/pe/tests/test_tax.py`.
    """

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        WA has no state EITC, so ``wa_eitc`` must not diverge from the federal
        credit. It is its own class only so the registry maps one key to one
        calculator. Asserting it overrides nothing is stricter than asserting
        identity with ``Eitc`` was: a subclass that added an input would still be a
        subclass, but would fail here.
        """
        self.assertTrue(issubclass(WaEitc, Eitc))
        self.assertEqual(WaEitc.pe_name, Eitc.pe_name)
        self.assertEqual(list(WaEitc.pe_inputs), list(Eitc.pe_inputs))
        self.assertEqual(list(WaEitc.pe_outputs), list(Eitc.pe_outputs))


class TestWaWftc(TestCase):
    """Tests for WaWftc calculator class wiring."""

    def test_exists_and_is_subclass_of_policy_engine_tax_unit_calculator(self):
        """WaWftc is a `PolicyEngineTaxUnitCalulator` (lives in the tax-unit entity)."""
        self.assertTrue(issubclass(WaWftc, PolicyEngineTaxUnitCalulator))

    def test_pe_name_targets_wa_working_families_tax_credit(self):
        """`pe_name` resolves to PolicyEngine's `wa_working_families_tax_credit` variable."""
        self.assertEqual(WaWftc.pe_name, "wa_working_families_tax_credit")

    def test_pe_inputs_includes_wa_state_code_dependency(self):
        """The WA state code is added on top of the federal Eitc inputs."""
        self.assertIn(WaStateCodeDependency, WaWftc.pe_inputs)

    def test_wa_state_code_dependency_is_configured_correctly(self):
        """Sanity-check the dependency itself."""
        self.assertEqual(WaStateCodeDependency.state, "WA")
        self.assertEqual(WaStateCodeDependency.field, "state_code")

    def test_pe_inputs_includes_all_federal_eitc_inputs(self):
        """All federal Eitc inputs flow through to WaWftc unchanged."""
        for parent_input in Eitc.pe_inputs:
            self.assertIn(parent_input, WaWftc.pe_inputs)

    def test_pe_inputs_adds_exactly_one_dependency_to_eitc(self):
        """WaWftc adds exactly one input on top of federal Eitc (the WA state code)."""
        self.assertEqual(len(WaWftc.pe_inputs), len(Eitc.pe_inputs) + 1)

    def test_pe_outputs_is_wa_wftc(self):
        """Output is the WA WFTC dollar value (not the federal EITC)."""
        self.assertEqual(WaWftc.pe_outputs, [tax_dependency.WaWftc])

    def test_wa_wftc_tax_dependency_targets_correct_field(self):
        """The WaWftc tax dependency points at PE's `wa_working_families_tax_credit` field."""
        self.assertEqual(tax_dependency.WaWftc.field, "wa_working_families_tax_credit")
