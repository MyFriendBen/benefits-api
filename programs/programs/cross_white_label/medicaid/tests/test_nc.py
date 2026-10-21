"""NC Medicaid wiring."""

from django.test import SimpleTestCase

from programs.framework.pe_dependencies.household import NcStateCodeDependency
from programs.framework.pe_dependencies.member import IsBlindDependency
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.medicaid.nc import NcMedicaid


class TestNcMedicaidWiring(SimpleTestCase):
    def test_program_code(self):
        self.assertEqual(NcMedicaid.program_code, "nc_medicaid")

    def test_pe_inputs_add_the_state_code_and_is_blind(self):
        """SSI is computed in our own code, so this always-on program is what keeps `is_blind`
        in NC's pooled PolicyEngine payload, where it feeds the aged/blind/disabled SSI
        classification the SSI-recipient Medicaid pathway reads."""
        self.assertEqual(
            set(NcMedicaid.pe_inputs) - set(Medicaid.pe_inputs), {NcStateCodeDependency, IsBlindDependency}
        )
