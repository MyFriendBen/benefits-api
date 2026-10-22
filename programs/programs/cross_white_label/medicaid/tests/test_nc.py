"""NC Medicaid wiring."""

from django.test import SimpleTestCase

from programs.framework.pe_dependencies.household import NcStateCodeDependency
from programs.framework.pe_dependencies.member import IsBlindDependency, MeetsSsiDisabilityCriteriaDependency
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.medicaid.nc import NcMedicaid


class TestNcMedicaidWiring(SimpleTestCase):
    def test_program_code(self):
        self.assertEqual(NcMedicaid.program_code, "nc_medicaid")

    def test_pe_inputs_add_the_state_code_and_the_ssi_disability_inputs(self):
        """SSI is computed in our own code and SNAP can be removed by a referrer, so this
        always-on program is what guarantees `is_blind` and `meets_ssi_disability_criteria` in
        NC's pooled PolicyEngine payload, where they gate the aged/blind/disabled Medicaid pathway."""
        self.assertEqual(
            set(NcMedicaid.pe_inputs) - set(Medicaid.pe_inputs),
            {NcStateCodeDependency, IsBlindDependency, MeetsSsiDisabilityCriteriaDependency},
        )
