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

That makes the MO-side facts worth pinning narrow: that each slug resolves to its
own class, and that the thin subclasses over ``Ctc`` and ``Eitc`` add nothing to
the federal calculators they wrap.

Everything else about the calculators (``pe_name``, ``pe_outputs``, the input set,
and the absence of a state code) is a property of the shared federal classes and
is asserted once in ``programs/programs/federal/pe/tests/test_tax.py``. Proving
these slugs *are* those objects extends those guarantees here.
"""

from django.test import TestCase

import programs.framework.pe_dependencies as dependency
from programs.programs.mo.pe.tax import MoWftc
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from integrations.clients.policyengine.registry import all_calculators
from programs.programs.cross_white_label.cdcc.base import Cdcc
from programs.programs.cross_white_label.cdcc.mo import MoCdccFederal
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.eitc.mo import MoEitc
from programs.programs.cross_white_label.ctc.base import Ctc
from programs.programs.cross_white_label.ctc.mo import MoCtc
from programs.programs.cross_white_label.aca.base import Aca
from programs.programs.cross_white_label.aca.mo import MoAca


class TestMoCtcWiring(TestCase):
    """mo_ctc registration against the shared federal Ctc calculator."""

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        MO has no state CTC, so ``mo_ctc`` must not diverge from the federal
        credit. It is its own class only so the registry maps one key to one
        calculator. Asserting it overrides nothing is stricter than asserting
        identity with ``Ctc`` was: a subclass that added an input would still be a
        subclass, but would fail here.
        """
        self.assertTrue(issubclass(MoCtc, Ctc))
        self.assertEqual(MoCtc.pe_name, Ctc.pe_name)
        self.assertEqual(list(MoCtc.pe_inputs), list(Ctc.pe_inputs))
        self.assertEqual(list(MoCtc.pe_outputs), list(Ctc.pe_outputs))


class TestMoEitcWiring(TestCase):
    """mo_eitc registration against the shared federal Eitc calculator."""

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        MO has no state EITC, so ``mo_eitc`` must not diverge from the federal
        credit. It is its own class only so the registry maps one key to one
        calculator. Asserting it overrides nothing is stricter than asserting
        identity with ``Eitc`` was: a subclass that added an input would still be a
        subclass, but would fail here.
        """
        self.assertTrue(issubclass(MoEitc, Eitc))
        self.assertEqual(MoEitc.pe_name, Eitc.pe_name)
        self.assertEqual(list(MoEitc.pe_inputs), list(Eitc.pe_inputs))
        self.assertEqual(list(MoEitc.pe_outputs), list(Eitc.pe_outputs))


class TestMoCdccFederalWiring(TestCase):
    """mo_cdcc_federal registration against the shared federal Cdcc calculator."""

    def test_is_the_federal_calculator_with_nothing_added(self):
        """A thin subclass of the federal calculator: same PE variable, same inputs.

        Missouri has no state CDCC, so ``mo_cdcc_federal`` must not diverge from the
        federal credit. It is its own class only so the registry maps one key to one
        calculator — Kansas registers ``ks_cdcc_federal`` against ``KsCdccFederal``
        for the same reason. Asserting it overrides nothing is stricter than the
        cross-state identity this replaced: a subclass that added an input would
        still be a subclass, but would fail here.
        """
        self.assertTrue(issubclass(MoCdccFederal, Cdcc))
        self.assertEqual(MoCdccFederal.pe_name, Cdcc.pe_name)
        self.assertEqual(list(MoCdccFederal.pe_inputs), list(Cdcc.pe_inputs))
        self.assertEqual(list(MoCdccFederal.pe_outputs), list(Cdcc.pe_outputs))


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
