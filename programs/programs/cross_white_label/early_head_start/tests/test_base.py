"""Recovered from pe/pe/tests."""

from django.test import TestCase
from programs.framework.pe_base import PolicyEngineMembersCalculator
from programs.framework.pe_dependencies import irs_gross_income, member, receipt_contract, spm
from programs.programs.cross_white_label.head_start.base import HeadStart
from programs.programs.cross_white_label.early_head_start.base import EarlyHeadStart
from programs.programs.cross_white_label.test_helpers import registered_subclasses, state_codes


class TestFederalEarlyHeadStart(TestCase):
    """Wiring of the shared federal Early Head Start (birth-3, pregnant women) calculator."""

    def test_is_a_member_calculator(self):
        self.assertTrue(issubclass(EarlyHeadStart, PolicyEngineMembersCalculator))

    def test_reads_the_person_level_pe_category(self):
        self.assertEqual(EarlyHeadStart.pe_category, "people")

    def test_pe_name_is_early_head_start(self):
        self.assertEqual(EarlyHeadStart.pe_name, "early_head_start")

    def test_pe_outputs_read_the_early_head_start_field(self):
        self.assertEqual(EarlyHeadStart.pe_outputs, [member.EarlyHeadStart])
        self.assertEqual(member.EarlyHeadStart.field, "early_head_start")

    def test_pe_inputs_include_age_pregnancy_and_foster_care(self):
        """EHS serves birth-3 (age) and pregnant women (pregnancy), plus the
        income-independent foster care pathway. Pregnancy is what distinguishes
        these inputs from ``HeadStart``'s."""
        self.assertIn(member.AgeDependency, EarlyHeadStart.pe_inputs)
        self.assertIn(member.PregnancyDependency, EarlyHeadStart.pe_inputs)
        self.assertIn(member.FosterCareDependency, EarlyHeadStart.pe_inputs)

    def test_pe_inputs_include_categorical_benefit_signals(self):
        for dep in receipt_contract:
            self.assertIn(dep, EarlyHeadStart.pe_inputs)
        self.assertIn(spm.ReceivesSnapDependency, EarlyHeadStart.pe_inputs)
        self.assertIn(spm.ReceivesTanfDependency, EarlyHeadStart.pe_inputs)
        self.assertIn(member.ReceivesSsiDependency, EarlyHeadStart.pe_inputs)

    def test_pe_inputs_include_irs_gross_income(self):
        for income_input in irs_gross_income:
            self.assertIn(income_input, EarlyHeadStart.pe_inputs)

    def test_federal_class_carries_no_state_code(self):
        self.assertEqual(state_codes(EarlyHeadStart), [])

    def test_pregnancy_is_not_sent_by_plain_head_start(self):
        """Only EHS serves pregnant women; sending pregnancy to ``head_start`` would
        be an input its formula ignores."""
        self.assertNotIn(member.PregnancyDependency, HeadStart.pe_inputs)
