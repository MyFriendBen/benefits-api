"""
Unit tests for the MO member-level PolicyEngine calculators.

``MoHeadStart`` and ``MoEarlyHeadStart`` are thin wrappers on the federal
``HeadStart`` / ``EarlyHeadStart`` PE calculators that add only the MO state code —
all eligibility and the per-individual value come from PolicyEngine's ``head_start`` /
``early_head_start`` variables with no MO-specific variance (mirrors
``TxHeadStart`` / ``KsHeadStart`` / ``MaHeadStart``).

The federal dependency logic is covered in
``policyengine/calculators/dependencies/tests/test_member.py`` and the MO state code in
``policyengine/calculators/dependencies/tests/test_household.py``; here we assert only
the MO wiring. The spec's dollar-value scenarios (Head Start: $16,314 per eligible child,
$32,629 for two children) are verified end-to-end against the live PolicyEngine API — see
``programs/programs/mo/head_start/spec.md``.
"""

from django.test import TestCase

from programs.programs.federal.pe.member import HeadStart, EarlyHeadStart
from programs.programs.policyengine.calculators.dependencies.household import MoStateCodeDependency
from programs.programs.policyengine.calculators.dependencies.member import (
    AgeDependency,
    PregnancyDependency,
    FosterCareDependency,
    Ssi,
    HeadStart as HeadStartOutput,
    EarlyHeadStart as EarlyHeadStartOutput,
)
from programs.programs.mo.pe import mo_member_calculators, mo_pe_calculators
from programs.programs.mo.pe.member import MoHeadStart, MoEarlyHeadStart


class TestMoHeadStartWiring(TestCase):
    """MoHeadStart (ages 3-5) registration and MO-specific pe_inputs handling."""

    def test_is_subclass_of_head_start(self):
        self.assertTrue(issubclass(MoHeadStart, HeadStart))

    def test_is_registered_in_mo_member_calculators(self):
        self.assertIn("mo_head_start", mo_member_calculators)
        self.assertEqual(mo_member_calculators["mo_head_start"], MoHeadStart)

    def test_is_registered_in_mo_pe_calculators(self):
        self.assertIn("mo_head_start", mo_pe_calculators)
        self.assertEqual(mo_pe_calculators["mo_head_start"], MoHeadStart)

    def test_pe_name_is_head_start(self):
        self.assertEqual(MoHeadStart.pe_name, "head_start")

    def test_pe_inputs_includes_mo_state_code(self):
        self.assertIn(MoStateCodeDependency, MoHeadStart.pe_inputs)

    def test_pe_inputs_preserve_federal_head_start_inputs(self):
        """The MO wrapper only appends the state code; it must not drop any federal input."""
        for dep in HeadStart.pe_inputs:
            self.assertIn(dep, MoHeadStart.pe_inputs)

    def test_pe_inputs_include_age_and_foster_pathways(self):
        """Ages 3-5 (age) and the foster-care categorical pathway per the spec."""
        self.assertIn(AgeDependency, MoHeadStart.pe_inputs)
        self.assertIn(FosterCareDependency, MoHeadStart.pe_inputs)

    def test_pe_inputs_include_categorical_benefit_signals(self):
        """SNAP / TANF / SSI feed PolicyEngine's categorical-eligibility determination."""
        self.assertIn(Ssi, MoHeadStart.pe_inputs)

    def test_pe_outputs_is_head_start_variable(self):
        self.assertEqual(MoHeadStart.pe_outputs, [HeadStartOutput])

    def test_mo_state_code_dependency_configured(self):
        self.assertEqual(MoStateCodeDependency.state, "MO")
        self.assertEqual(MoStateCodeDependency.field, "state_code")


class TestMoEarlyHeadStartWiring(TestCase):
    """MoEarlyHeadStart (birth-3 / pregnant) registration and MO-specific pe_inputs handling."""

    def test_is_subclass_of_early_head_start(self):
        self.assertTrue(issubclass(MoEarlyHeadStart, EarlyHeadStart))

    def test_is_registered_in_mo_member_calculators(self):
        self.assertIn("mo_early_head_start", mo_member_calculators)
        self.assertEqual(mo_member_calculators["mo_early_head_start"], MoEarlyHeadStart)

    def test_pe_name_is_early_head_start(self):
        self.assertEqual(MoEarlyHeadStart.pe_name, "early_head_start")

    def test_pe_inputs_includes_mo_state_code(self):
        self.assertIn(MoStateCodeDependency, MoEarlyHeadStart.pe_inputs)

    def test_pe_inputs_preserve_federal_early_head_start_inputs(self):
        for dep in EarlyHeadStart.pe_inputs:
            self.assertIn(dep, MoEarlyHeadStart.pe_inputs)

    def test_pe_inputs_include_age_pregnancy_and_foster_pathways(self):
        self.assertIn(AgeDependency, MoEarlyHeadStart.pe_inputs)
        self.assertIn(PregnancyDependency, MoEarlyHeadStart.pe_inputs)
        self.assertIn(FosterCareDependency, MoEarlyHeadStart.pe_inputs)

    def test_pe_outputs_is_early_head_start_variable(self):
        self.assertEqual(MoEarlyHeadStart.pe_outputs, [EarlyHeadStartOutput])

    def test_does_not_reuse_head_start_variable(self):
        """EHS must resolve PE's ``early_head_start`` variable, not the ``head_start`` one."""
        self.assertNotEqual(MoEarlyHeadStart.pe_name, "head_start")
