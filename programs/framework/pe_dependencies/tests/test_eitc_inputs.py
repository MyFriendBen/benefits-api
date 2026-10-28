"""The `eitc_inputs` bundle the state EITCs and working-family credits spread."""

from django.test import SimpleTestCase

import programs.framework.pe_dependencies as dependency
from programs.framework.pe_dependencies.household import StateCode


class TestEitcInputs(SimpleTestCase):
    def test_sends_no_state_code(self):
        """Each credit adds its own state code; the shared set must not pick one for it."""
        self.assertFalse([dep for dep in dependency.eitc_inputs if issubclass(dep, StateCode)])
