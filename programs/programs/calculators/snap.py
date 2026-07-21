"""
SnapCalculator: the one override ConfigurableCalculator's own docstring
earmarked for "a future subclass" (see calculators/base.py's
household_value()). Reproduces federal Snap.household_value()'s real
behavior (federal/pe/spm.py:42-43):

    return int(self.sim.value(...)) * 12

i.e. cast the monthly PE value to int *first*, then multiply by 12 -- not
the reverse, which gives a different (wrong) answer for any non-integer
monthly value. get_spm_value already casts internally, so calling it and
multiplying the result by 12 outside reproduces that exact order (see
DECISIONS.md D-013).
"""

from __future__ import annotations

from programs.programs.calculators.base import ConfigurableCalculator


class SnapCalculator(ConfigurableCalculator):
    def household_value(self) -> int:
        return self.client.get_spm_value(self.config.pe_name, period=self.pe_output_period) * 12
