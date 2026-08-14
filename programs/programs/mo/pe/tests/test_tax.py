"""
Unit tests for the MO tax-unit PolicyEngine calculator registrations.

Missouri has no state CTC, EITC, or CDCC and no MO-specific variance, so
``mo_ctc``, ``mo_eitc``, and ``mo_cdcc_federal`` map straight to the shared
federal ``Ctc``, ``Eitc``, and ``Cdcc`` classes rather than subclasses — the same
treatment as ``ks_ctc``, ``ks_cdcc_federal``, ``tx_ctc``/``tx_eitc``, and
``wa_ctc``/``wa_eitc``.

``mo_aca_ptc`` is the exception: ACA PTC eligibility is federal, but its dollar
value is county-driven, so ``MoAca`` is a real subclass carrying the two extra
inputs Missouri's value depends on.

That makes registration the only MO-side fact to pin, and one part of it is
load-bearing: ``mo_tax_unit_calculators`` must be spread into the global
``all_tax_unit_calculators`` in ``registry.py``. ``screener.views`` resolves
``Program.name_abbreviated`` against ``all_calculators``, so a program registered
only in ``mo_pe_calculators`` is invisible to it and silently returns no value.

Everything else about the calculators (``pe_name``, ``pe_outputs``, the input set,
and the absence of a state code) is a property of the shared federal classes and
is asserted once in ``programs/programs/federal/pe/tests/test_tax.py``. Proving
these slugs *are* those objects extends those guarantees here.
"""

from django.test import TestCase

import programs.framework.pe_dependencies as dependency
from programs.programs.federal.pe.tax import Aca, Cdcc, Ctc, Eitc
from programs.programs.mo.pe import mo_pe_calculators, mo_tax_unit_calculators
from programs.programs.mo.pe.tax import MoAca
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from integrations.clients.policyengine.registry import (
    all_calculators,
    all_tax_unit_calculators,
)


class TestMoCtcWiring(TestCase):
    """mo_ctc registration against the shared federal Ctc calculator."""

    def test_is_federal_ctc_everywhere(self):
        self.assertIs(mo_tax_unit_calculators["mo_ctc"], Ctc)
        self.assertIs(mo_pe_calculators["mo_ctc"], Ctc)
        self.assertIs(all_tax_unit_calculators["mo_ctc"], Ctc)
        self.assertIs(all_calculators["mo_ctc"], Ctc)

    def test_matches_builtin_federal_registry_key(self):
        """Same calculator the federal registry serves as ``ctc`` — no MO subclass."""
        self.assertIs(all_tax_unit_calculators["mo_ctc"], all_tax_unit_calculators["ctc"])


class TestMoEitcWiring(TestCase):
    """mo_eitc registration against the shared federal Eitc calculator."""

    def test_is_federal_eitc_everywhere(self):
        self.assertIs(mo_tax_unit_calculators["mo_eitc"], Eitc)
        self.assertIs(mo_pe_calculators["mo_eitc"], Eitc)
        self.assertIs(all_tax_unit_calculators["mo_eitc"], Eitc)
        self.assertIs(all_calculators["mo_eitc"], Eitc)

    def test_matches_builtin_federal_registry_key(self):
        """Same calculator the federal registry serves as ``eitc`` — no MO subclass."""
        self.assertIs(all_tax_unit_calculators["mo_eitc"], all_tax_unit_calculators["eitc"])


class TestMoCdccFederalWiring(TestCase):
    """mo_cdcc_federal registration against the shared federal Cdcc calculator."""

    def test_is_federal_cdcc_everywhere(self):
        self.assertIs(mo_tax_unit_calculators["mo_cdcc_federal"], Cdcc)
        self.assertIs(mo_pe_calculators["mo_cdcc_federal"], Cdcc)
        self.assertIs(all_tax_unit_calculators["mo_cdcc_federal"], Cdcc)
        self.assertIs(all_calculators["mo_cdcc_federal"], Cdcc)

    def test_matches_the_other_states_federal_cdcc(self):
        """Kansas registers the same shared class under ``ks_cdcc_federal``. Unlike
        ``ctc``/``eitc``, the federal registry exposes no bare ``cdcc`` key, so the
        cross-state identity is what pins "no MO subclass"."""
        self.assertIs(
            all_tax_unit_calculators["mo_cdcc_federal"],
            all_tax_unit_calculators["ks_cdcc_federal"],
        )


class TestMoAcaWiring(TestCase):
    """mo_aca_ptc registration and the MO-specific inputs on MoAca."""

    def test_registered_under_config_name_abbreviated(self):
        """The registry key must equal the program's ``name_abbreviated`` in
        ``mo_aca_ptc_initial_config.json`` — ``screener.views`` resolves calculators by
        that string, so a mismatch silently returns no value."""
        self.assertIs(mo_tax_unit_calculators["mo_aca_ptc"], MoAca)
        self.assertIs(mo_pe_calculators["mo_aca_ptc"], MoAca)
        self.assertIs(all_tax_unit_calculators["mo_aca_ptc"], MoAca)
        self.assertIs(all_calculators["mo_aca_ptc"], MoAca)

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
