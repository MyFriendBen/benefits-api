"""
Unit tests for MA TAFDC PolicyEngine eligibility (MFB-232).

TAFDC pregnancy eligibility in PolicyEngine requires `current_pregnancy_month >= 5`.
We don't collect pregnancy month, so `MaTafdcPregnancyEligibleDependency` sends
`ma_tafdc_pregnancy_eligible = true` for any pregnant member so TAFDC shows.
"""

from unittest.mock import Mock

from django.test import TestCase

from programs.programs.ma.pe.spm import MaTafdc
from programs.programs.policyengine.calculators.dependencies.member import (
    MaTafdcPregnancyEligibleDependency,
    PregnancyDependency,
)


class TestMaTafdcPregnancyEligibleDependency(TestCase):
    """Tests for the MaTafdcPregnancyEligibleDependency value logic."""

    def _dependency(self, pregnant):
        member = Mock()
        member.pregnant = pregnant
        return MaTafdcPregnancyEligibleDependency(Mock(), member, Mock())

    def test_value_true_when_pregnant(self) -> None:
        self.assertTrue(self._dependency(True).value())

    def test_value_false_when_not_pregnant(self) -> None:
        self.assertFalse(self._dependency(False).value())

    def test_value_false_when_pregnant_is_none(self) -> None:
        # `pregnant` is a nullable BooleanField; an unanswered value must not crash.
        self.assertFalse(self._dependency(None).value())


class TestMaTafdcPeInputs(TestCase):
    """Tests for the MaTafdc calculator wiring."""

    def test_includes_ma_tafdc_pregnancy_eligible_dependency(self) -> None:
        self.assertIn(MaTafdcPregnancyEligibleDependency, MaTafdc.pe_inputs)

    def test_still_includes_pregnancy_dependency(self) -> None:
        # PregnancyDependency sends `is_pregnant`, which PE's teen-parent branch
        # reads. It must remain alongside the new dependency, not be replaced.
        self.assertIn(PregnancyDependency, MaTafdc.pe_inputs)
