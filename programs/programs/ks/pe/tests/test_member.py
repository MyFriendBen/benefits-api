"""
Unit tests for the KS member-level PolicyEngine calculators (KsKanCare / KS Medicaid,
KsChip / KS CHIP, and KsMsp / KS Medicare Savings Program).

KsKanCare coverage is two layers:

1. **Wiring** — KsKanCare subclasses the federal ``Medicaid`` calculator, is registered
   as ``ks_medicaid``, and carries the KS-specific ``pe_inputs`` handling from the spec's
   Implementation Notes 1–2:
     - the federal ``SsiCountableResourcesDependency`` is sent (ABD asset test screened),
     - ``MeetsSsiDisabilityCriteriaDependency`` + ``IsBlindDependency`` are added (disability /
       blindness mapping), and ``KsStateCodeDependency`` selects KS parameters.

2. **Scenario coverage** — one test per scenario in the ``## Test Scenarios`` section of
   ``programs/programs/ks/medicaid/spec.md``. Because these unit tests run without the live
   PolicyEngine API, PolicyEngine's determination for each scenario is mocked
   (``get_member_variable`` = the ``medicaid`` variable; ``get_member_dependency_value`` =
   ``MedicaidCategory`` / ``is_optional_senior_or_disabled_for_medicaid``) exactly as the spec
   documents PE returning for that household. The assertion is on the KS calculator's MFB-side
   output: the per-member dollar value and the value-tier routing (MAGI $3,648 / AGED $20,508 /
   DISABLED $32,460, and DISABLED-over-AGED priority). The FPL/FBR threshold math itself lives in
   PolicyEngine and is verified end-to-end by the spec's PolicyEngine run.

Scenarios 12 (already-enrolled suppression) and 13 (no-separate-unborn-enrollee) are MFB
display-layer / household-construction rules with no calculator logic, so they are not unit-tested
here — see the spec's Implementation Notes.
"""

from unittest.mock import Mock, MagicMock

from django.test import TestCase

from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import member as member_deps
from programs.framework.pe_dependencies.household import KsStateCodeDependency
from programs.framework.pe_dependencies.member import (
    AgeDependency,
    PregnancyDependency,
    Chip,
)
from programs.framework.pe_dependencies.tax import KsChipPremium
from programs.programs.cross_white_label.medicaid.base import Medicaid
from programs.programs.cross_white_label.medicaid.ks import KsKanCare
from programs.programs.cross_white_label.msp.ks import KsMsp
from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
from programs.programs.cross_white_label.early_head_start.ks import KsEarlyHeadStart
from programs.programs.cross_white_label.medicaid.chip.ks import KsChip

# Annual value tiers (medicaid_categories * 12)
MAGI = 3_648  # INFANT / YOUNG_CHILD / OLDER_CHILD / PREGNANT / PARENT / ADULT / YOUNG_ADULT
AGED = 20_508
DISABLED = 32_460


class TestKsChip(TestCase):
    """Tests for the KsChip calculator class."""

    def test_exists_and_is_subclass_of_policy_engine_members_calculator(self):
        """KsChip exists and follows the member-level calculator pattern."""
        self.assertTrue(issubclass(KsChip, PolicyEngineMembersCalculator))
        self.assertIsNotNone(KsChip.pe_inputs)
        self.assertGreater(len(KsChip.pe_inputs), 0)

    def test_pe_name_is_chip(self):
        """KsChip reads PolicyEngine's federal `chip` output."""
        self.assertEqual(KsChip.pe_name, "chip")

    def test_pe_inputs_includes_age_dependency(self):
        """CHIP eligibility is age-gated (under 19)."""
        self.assertIn(AgeDependency, KsChip.pe_inputs)
        self.assertEqual(AgeDependency.field, "age")

    def test_pe_inputs_includes_pregnancy_dependency(self):
        """PregnancyDependency mirrors the federal Chip inputs."""
        self.assertIn(PregnancyDependency, KsChip.pe_inputs)
        self.assertEqual(PregnancyDependency.field, "is_pregnant")

    def test_pe_inputs_match_ks_medicaid_inputs(self):
        """CHIP gates on ~is_medicaid_eligible, and every program on a screen shares one
        PolicyEngine simulation, so CHIP must send the exact same KS Medicaid inputs as
        KsKanCare — otherwise the shared medicaid computation would be inconsistent."""
        self.assertEqual(KsChip.pe_inputs, KsKanCare.pe_inputs)

    def test_pe_inputs_includes_all_ks_medicaid_inputs(self):
        """CHIP reuses KsKanCare.pe_inputs verbatim, so it carries every KS Medicaid input."""
        for kancare_input in KsKanCare.pe_inputs:
            self.assertIn(kancare_input, KsChip.pe_inputs)

    def test_pe_inputs_includes_ssi_countable_resources(self):
        """Inherited via KsKanCare.pe_inputs; CHIP applies no resource test of its own."""
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsChip.pe_inputs)

    def test_pe_inputs_includes_ks_state_code_dependency(self):
        """KsStateCodeDependency sets state_code=KS so PE applies the KS income limit (2.55)."""
        self.assertIn(KsStateCodeDependency, KsChip.pe_inputs)
        self.assertEqual(KsStateCodeDependency.state, "KS")
        self.assertEqual(KsStateCodeDependency.field, "state_code")

    def test_pe_outputs_includes_chip_dependency(self):
        """The per-child coverage value comes from PE's `chip` output."""
        self.assertIn(Chip, KsChip.pe_outputs)
        self.assertEqual(Chip.field, "chip")

    def test_pe_outputs_includes_ks_chip_premium_dependency(self):
        """KS additionally surfaces the tax-unit-level `ks_chip_premium`."""
        self.assertIn(KsChipPremium, KsChip.pe_outputs)
        self.assertEqual(KsChipPremium.field, "ks_chip_premium")
        self.assertEqual(KsChipPremium.unit, "tax_units")

    def test_member_value_returns_pe_value_when_member_has_no_insurance(self):
        """An uninsured child receives the full PE-calculated coverage value."""
        calculator = KsChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        pe_value = 1896
        calculator.get_member_variable = Mock(return_value=pe_value)

        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=True)

        result = calculator.member_value(member)

        self.assertEqual(result, pe_value)
        member.has_insurance_types.assert_called_once_with(("none",))

    def test_member_value_returns_zero_when_member_has_insurance(self):
        """A child with any other coverage is zeroed out (uninsured-only rule)."""
        calculator = KsChip(Mock(), Mock(), Mock())
        calculator._sim = MagicMock()

        pe_value = 1896
        calculator.get_member_variable = Mock(return_value=pe_value)

        member = Mock()
        member.id = 1
        member.has_insurance_types = Mock(return_value=False)

        result = calculator.member_value(member)

        self.assertEqual(result, 0)
        member.has_insurance_types.assert_called_once_with(("none",))


class TestKsMspWiring(TestCase):
    """
    KS-specific MSP wiring. The shared contract every state's MSP must satisfy (pe_name,
    pe_category, pe_outputs, no federal input dropped, the Medicaid input set, exactly one
    state code matching the slug, no ``member_value`` override) is asserted once for all
    registered subclasses in ``federal/pe/tests/test_msp.py``.
    """

    def test_program_code_is_ks_medicare_savings(self):
        self.assertEqual(KsMsp.program_code, "ks_medicare_savings")

    def test_pe_name_is_msp(self):
        self.assertEqual(KsMsp.pe_name, "msp")

    def test_pe_inputs_includes_ks_state_code(self):
        """Resolves the MSP asset-test-applies parameter, which is true for Kansas."""
        self.assertIn(KsStateCodeDependency, KsMsp.pe_inputs)

    def test_pe_inputs_includes_medicaid_inputs(self):
        """MSP needs *Medicaid.pe_inputs for the QI ~is_medicaid_eligible check and for the
        msp_asset_eligible resource test."""
        for medicaid_input in Medicaid.pe_inputs:
            self.assertIn(medicaid_input, KsMsp.pe_inputs)

    def test_pe_inputs_includes_ssi_countable_resources(self):
        """Without it, msp_asset_eligible sees $0 and an over-asset applicant wrongly qualifies."""
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsMsp.pe_inputs)


class TestKsMspKanCareAssetConsistency(TestCase):
    """KanCare and MSP both read ssi_countable_resources in one shared simulation, so they must
    screen assets identically — sending it from one but not the other corrupts that program's
    eligibility. These assertions fail if the two ever diverge."""

    def test_kancare_and_msp_agree_on_ssi_countable_resources(self):
        kancare_sends = member_deps.SsiCountableResourcesDependency in KsKanCare.pe_inputs
        msp_sends = member_deps.SsiCountableResourcesDependency in KsMsp.pe_inputs
        self.assertEqual(kancare_sends, msp_sends)

    def test_both_send_ssi_countable_resources(self):
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsKanCare.pe_inputs)
        self.assertIn(member_deps.SsiCountableResourcesDependency, KsMsp.pe_inputs)


class TestKsEarlyHeadStartWiring(TestCase):
    """
    KS-specific wiring for Early Head Start (birth-3 / pregnant). A thin wrapper on
    the federal ``EarlyHeadStart`` PE calculator, adding only the KS state code.

    The shared contract (pe_name, pe_outputs, no federal input dropped, exactly one
    state code matching the slug, no ``member_value`` override) is asserted once for
    all registered subclasses in ``federal/pe/tests/test_head_start.py``.

    The spec's dollar-value scenarios ($13,323 per eligible individual) are verified
    end-to-end against the live PolicyEngine API — see
    ``programs/programs/ks/early_head_start/spec.md``.
    """

    def test_pe_inputs_includes_ks_state_code(self):
        self.assertTrue(issubclass(KsEarlyHeadStart, EarlyHeadStart))
        self.assertIn(KsStateCodeDependency, KsEarlyHeadStart.pe_inputs)
