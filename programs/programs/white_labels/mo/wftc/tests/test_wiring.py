"""MO WFTC wiring."""

from django.test import TestCase
import programs.framework.pe_dependencies as dependency
from integrations.clients.policyengine.registry import all_calculators
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.eitc.mo import MoEitc
from programs.programs.white_labels.mo.wftc.calculator import MoWftc


class TestMoWftcWiring(TestCase):
    """mo_wftc registration and the inputs MoWftc adds to the federal Eitc set."""

    def test_registered_under_config_name_abbreviated(self):
        """The ``program_code`` must equal the program's ``name_abbreviated`` in
        ``mo_wftc_initial_config.json`` — the registry keys off it, and
        ``screener.views`` resolves calculators by that string, so a mismatch
        silently returns no value."""
        self.assertEqual(MoWftc.program_code, "mo_wftc")
        self.assertIs(all_calculators["mo_wftc"], MoWftc)

    def test_reads_missouris_own_credit(self):
        """Missouri's own variable, not the federal ``eitc``."""
        self.assertEqual(MoWftc.pe_name, "mo_wftc")
        self.assertEqual(MoWftc.pe_outputs, [dependency.tax.MoWftc])

    def test_sends_mo_state_code(self):
        self.assertIn(dependency.household.MoStateCodeDependency, MoWftc.pe_inputs)

    def test_sends_real_estate_taxes(self):
        """Not in the federal Eitc set. Without it the liability cap is never
        reduced: scenario 14 flips to eligible and scenario 16 pays $34, not $14."""
        self.assertIn(dependency.member.PropertyTaxExpenseDependency, MoWftc.pe_inputs)

    def test_preserves_every_federal_eitc_input(self):
        """MO adds inputs, it never drops one."""
        for federal_input in Eitc.pe_inputs:
            self.assertIn(federal_input, MoWftc.pe_inputs)

    def test_adds_exactly_the_two_extra_inputs(self):
        added = [dep for dep in MoWftc.pe_inputs if dep not in Eitc.pe_inputs]
        self.assertCountEqual(
            added,
            [
                dependency.member.PropertyTaxExpenseDependency,
                dependency.household.MoStateCodeDependency,
            ],
        )
