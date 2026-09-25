"""Payload assembly when several calculators are requested together.

One request carries every calculator a screen needs, so the payload builder has to
merge their inputs rather than emit one household per program. These assert the
merge for pairs that reach different entity levels — SNAP is SPM-scoped, WIC, SSI
and CHIP are per-member, EITC and ACA are tax-unit — since that is where a naive
merge drops a field.
"""

from programs.framework.pe_dependencies.payload import pe_input
from programs.framework.pe_dependencies.constants import MAIN_TAX_UNIT
from programs.programs.cross_white_label.aca.base import Aca
from programs.programs.cross_white_label.eitc.base import Eitc
from programs.programs.cross_white_label.medicaid.chip.base import Chip
from programs.programs.cross_white_label.snap.base import Snap
from programs.programs.cross_white_label.ssi.base import Ssi
from programs.programs.cross_white_label.wic.base import Wic
from programs.programs.testing_fixtures.pe_input_test_base import PeInputTestCase


class TestCombinedCalculatorsPeInput(PeInputTestCase):
    """Tests for pe_input with multiple calculators combined."""

    def test_snap_and_wic_combined(self):
        """Test that pe_input handles both Snap and Wic together."""
        result = pe_input(self.screen, [Snap, Wic])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        # Wic fields
        self.assertIn("wic", people[head_id])
        self.assertIn("employment_income", people[head_id])

        # Snap fields
        self.assertIn("snap_assets", spm_unit)
        self.assertIn("snap_if_takes_up", spm_unit)

    def test_eitc_and_snap_combined(self):
        """Test that pe_input handles both Eitc and Snap together."""
        result = pe_input(self.screen, [Eitc, Snap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        tax_units = household["tax_units"]

        # Eitc fields
        self.assertIn(MAIN_TAX_UNIT, tax_units)
        self.assertIn("eitc", tax_units[MAIN_TAX_UNIT])

        # Snap fields
        self.assertIn("snap_if_takes_up", spm_unit)

    def test_ssi_and_snap_combined(self):
        """Test that pe_input handles both Ssi and Snap together."""
        result = pe_input(self.screen, [Ssi, Snap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        # Ssi fields
        self.assertIn("ssi", people[head_id])
        self.assertIn("ssi_countable_resources", people[head_id])

        # Snap fields
        self.assertIn("snap_if_takes_up", spm_unit)

    def test_chip_and_snap_combined(self):
        """Test that pe_input handles both Chip and Snap together."""
        result = pe_input(self.screen, [Chip, Snap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        people = household["people"]
        head_id = str(self.head.id)

        # Chip fields
        self.assertIn("chip_category", people[head_id])

        # Snap fields
        self.assertIn("snap_if_takes_up", spm_unit)

    def test_aca_and_snap_combined(self):
        """Test that pe_input handles both Aca and Snap together."""
        result = pe_input(self.screen, [Aca, Snap])
        household = result["household"]
        spm_unit = household["spm_units"]["spm_unit"]
        tax_units = household["tax_units"]

        # Aca fields
        self.assertIn("aca_ptc", tax_units[MAIN_TAX_UNIT])

        # Snap fields
        self.assertIn("snap_if_takes_up", spm_unit)
