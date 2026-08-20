"""Recovered from pe/pe/tests."""

from integrations.clients.policyengine.policy_engine import pe_input
from programs.framework.pe_dependencies.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.snap.tx import TxSnap
from programs.programs.cross_white_label.tanf.tx import TxTanf
from programs.programs.cross_white_label.wic.tx import TxWic
from programs.programs.cross_white_label.ssi.tx import TxSsi
from programs.programs.cross_white_label.aca.tx import TxAca
from programs.programs.cross_white_label.medicaid.chip.tx import TxChip
from programs.framework.tests.pe_input_test_base import TxPeInputTestBase
from programs.framework.pe_dependencies import household


class TestTxCombinedCalculatorsPeInput(TxPeInputTestBase):
    """Tests for pe_input with multiple TX calculators combined."""

    def test_snap_and_wic_combined(self):
        """Test that pe_input handles both TxSnap and TxWic together."""
        result = pe_input(self.screen, [TxSnap, TxWic])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        # TxWic fields
        self.assertIn("wic", people[head_id])
        self.assertIn("employment_income", people[head_id])

        # TxSnap fields
        self.assertIn("snap_assets", spm_unit)
        self.assertIn("snap_if_takes_up", spm_unit)

    def test_eitc_and_snap_combined(self):
        """Test that pe_input handles both Eitc and TxSnap together."""
        result = pe_input(self.screen, [Eitc, TxSnap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        tax_units = household["tax_units"]

        # Eitc fields
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn("eitc", tax_units[MAIN_TAX_UNIT])

        # TxSnap fields
        self.assertIn("snap_if_takes_up", spm_unit)

    def test_ssi_and_snap_combined(self):
        """Test that pe_input handles both TxSsi and TxSnap together."""
        result = pe_input(self.screen, [TxSsi, TxSnap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        # TxSsi fields
        self.assertIn("ssi", people[head_id])
        self.assertIn("ssi_countable_resources", people[head_id])

        # TxSnap fields
        self.assertIn("snap_if_takes_up", spm_unit)

    def test_chip_and_snap_combined(self):
        """Test that pe_input handles both TxChip and TxSnap together."""
        result = pe_input(self.screen, [TxChip, TxSnap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        # TxChip fields
        self.assertIn("chip", people[head_id])

        # TxSnap fields
        self.assertIn("snap_if_takes_up", spm_unit)

    def test_aca_and_snap_combined(self):
        """Test that pe_input handles both TxAca and TxSnap together."""
        result = pe_input(self.screen, [TxAca, TxSnap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        tax_units = household["tax_units"]

        # TxAca fields
        self.assertIn("aca_ptc", tax_units[MAIN_TAX_UNIT])

        # TxSnap fields
        self.assertIn("snap_if_takes_up", spm_unit)

    def test_all_state_codes_match(self):
        """Test that state_code is TX regardless of which calculator is used."""
        calculators = [TxSnap, TxWic, Eitc, TxSsi, TxTanf, TxChip, TxAca]

        for calc in calculators:
            result = pe_input(self.screen, [calc])
            household_unit = result["household"]["households"]["household"]

            if household_unit.get("state_code"):
                period_key = list(household_unit["state_code"].keys())[0]
                self.assertEqual(
                    household_unit["state_code"][period_key],
                    "TX",
                    f"state_code should be TX for {calc.__name__}",
                )
