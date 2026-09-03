"""KS ACA PTC wiring tests.

No cassette and no ``integration`` marker: everything here is about which dependencies
``KsAca`` declares, which is our code's decision. The dollar values PolicyEngine returns for
the ``specs/ks.md`` scenarios are asserted in ``test_ks_scenarios.py``.
"""

from django.test import TestCase

import programs.framework.pe_dependencies as dependency
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from programs.programs.cross_white_label.aca.base import Aca
from programs.programs.cross_white_label.aca.ks import KsAca

KS_INPUTS = (
    dependency.household.KsStateCodeDependency,
    dependency.household.KsCountyDependency,
    dependency.member.HasEsiDependency,
)


class TestKsAcaWiring(TestCase):
    """ks_aca_ptc registration and the KS-specific inputs on KsAca."""

    def test_subclasses_federal_aca(self):
        self.assertTrue(issubclass(KsAca, Aca))
        self.assertTrue(issubclass(KsAca, PolicyEngineTaxUnitCalulator))

    def test_pe_name_is_federal_aca_ptc(self):
        """Eligibility and the formula are federal (26 U.S.C. 36B) — Kansas reads the same
        PolicyEngine variable, it just feeds it more inputs. Kansas uses HealthCare.gov, so
        there is no state-exchange layer to model either."""
        self.assertEqual(KsAca.pe_name, "aca_ptc")
        self.assertEqual(KsAca.pe_name, Aca.pe_name)

    def test_pe_outputs_unchanged_from_federal(self):
        self.assertEqual(KsAca.pe_outputs, Aca.pe_outputs)

    def test_sends_ks_state_code(self):
        self.assertIn(dependency.household.KsStateCodeDependency, KsAca.pe_inputs)

    def test_sends_county(self):
        """PolicyEngine keys the benchmark premium (SLCSP) off ``county_str``, not
        ``zip_code``: ``slcsp_rating_area_default`` looks the county token up in
        ``aca_rating_areas.csv`` and falls back to rating area 1 for anything it can't match.
        Kansas has 7 rating areas, so without county every household is priced as if it were
        in area 1 — Wyandotte's."""
        self.assertIn(dependency.household.KsCountyDependency, KsAca.pe_inputs)

    def test_sends_has_esi(self):
        """Employer coverage is a statutory disqualifier PolicyEngine applies only if we
        send ``has_esi``; without it a household with job-based coverage scores eligible for
        the full credit."""
        self.assertIn(dependency.member.HasEsiDependency, KsAca.pe_inputs)

    def test_preserves_every_federal_input(self):
        """KS adds inputs, it never drops one."""
        for federal_input in Aca.pe_inputs:
            self.assertIn(federal_input, KsAca.pe_inputs)

    def test_adds_exactly_the_three_ks_inputs(self):
        added = [dep for dep in KsAca.pe_inputs if dep not in Aca.pe_inputs]
        self.assertCountEqual(added, KS_INPUTS)

    def test_county_gates_calculation(self):
        """``KsCountyDependency`` declares ``county`` as a dependency, so a screen with no
        county is skipped by ``can_calc()`` instead of raising inside ``pe_input()`` and
        taking down every PolicyEngine program on the screen."""
        self.assertIn("county", dependency.household.KsCountyDependency.dependencies)

    def test_kansas_has_no_independent_cities(self):
        """All 105 Kansas counties are ordinary counties, so the base normalizer's
        ``NAME_COUNTY_KS`` token matches PolicyEngine's table for every one of them — no
        special case like Missouri's St. Louis City. Verified by cross-checking the KS
        white label's ``counties_by_zipcode`` against PolicyEngine's
        ``aca_rating_areas.csv``: 105 counties, exact match both directions."""
        self.assertEqual(dependency.household.KsCountyDependency.independent_cities, ())
