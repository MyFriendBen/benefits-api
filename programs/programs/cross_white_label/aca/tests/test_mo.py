"""MO tests."""

from programs.programs.cross_white_label.aca.base import Aca
from programs.programs.cross_white_label.aca.mo import MoAca
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from django.test import TestCase
import programs.framework.pe_dependencies as dependency


class TestMoAcaWiring(TestCase):
    """mo_aca_ptc registration and the MO-specific inputs on MoAca."""

    def test_subclasses_federal_aca(self):
        self.assertTrue(issubclass(MoAca, Aca))
        self.assertTrue(issubclass(MoAca, PolicyEngineTaxUnitCalulator))

    def test_pe_name_is_federal_aca_ptc(self):
        """Eligibility and the formula are federal (26 U.S.C. 36B) — MO reads the same
        PolicyEngine variable, it just feeds it more inputs."""
        self.assertEqual(MoAca.pe_name, "aca_ptc")
        self.assertEqual(MoAca.pe_name, Aca.pe_name)

    def test_pe_outputs_unchanged_from_federal(self):
        self.assertEqual(MoAca.pe_outputs, Aca.pe_outputs)

    def test_sends_mo_state_code(self):
        self.assertIn(dependency.household.MoStateCodeDependency, MoAca.pe_inputs)

    def test_sends_county(self):
        """PolicyEngine keys the benchmark premium (SLCSP) off ``county_str``, not
        ``zip_code``: without county, Jackson and Boone return the same SLCSP and both
        scenario values are wrong."""
        self.assertIn(dependency.household.MoCountyDependency, MoAca.pe_inputs)

    def test_sends_has_esi(self):
        """Employer coverage is a statutory disqualifier PolicyEngine applies only if we
        send ``has_esi``; without it a household with job-based coverage scores eligible."""
        self.assertIn(dependency.member.HasEsiDependency, MoAca.pe_inputs)

    def test_preserves_every_federal_input(self):
        """MO adds inputs, it never drops one."""
        for federal_input in Aca.pe_inputs:
            self.assertIn(federal_input, MoAca.pe_inputs)

    def test_adds_exactly_the_three_mo_inputs(self):
        added = [dep for dep in MoAca.pe_inputs if dep not in Aca.pe_inputs]
        self.assertCountEqual(
            added,
            [
                dependency.household.MoStateCodeDependency,
                dependency.household.MoCountyDependency,
                dependency.member.HasEsiDependency,
            ],
        )

    def test_county_gates_calculation(self):
        """``MoCountyDependency`` declares ``county`` as a dependency, so a screen with no
        county is skipped by ``can_calc()`` instead of raising inside ``pe_input()`` and
        taking down every PolicyEngine program on the screen."""
        self.assertIn("county", dependency.household.MoCountyDependency.dependencies)
