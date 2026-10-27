"""The `eitc_inputs` bundle the state EITCs and working-family credits spread.

Those credits' own tests compare against the bundle, so a missing item would pass there;
this pins what the bundle itself holds.
"""

from django.test import SimpleTestCase

import programs.framework.pe_dependencies as dependency
from programs.framework.pe_dependencies.household import StateCode


class TestEitcInputs(SimpleTestCase):
    def test_holds_age_tax_unit_structure_and_every_irs_income_stream(self):
        self.assertEqual(
            dependency.eitc_inputs,
            [
                dependency.member.AgeDependency,
                dependency.member.TaxUnitSpouseDependency,
                dependency.member.TaxUnitDependentDependency,
                *dependency.irs_gross_income,
            ],
        )

    def test_sends_no_state_code(self):
        """Each credit adds its own state code; the shared set must not pick one for it."""
        self.assertFalse([dep for dep in dependency.eitc_inputs if issubclass(dep, StateCode)])
