from django.test import TestCase

from programs.models import Program
from screener.models import WhiteLabel


class ProgramNameAbbreviatedNormalizationTests(TestCase):
    """Program.save() lowercases name_abbreviated so the case-sensitive key the
    calculator registry and the frontend current_benefits round-trip rely on is
    enforced at the data layer, not just by convention (MFB-720)."""

    def setUp(self):
        self.white_label = WhiteLabel.objects.create(name="Test State", code="test", state_code="TS")

    def test_new_program_lowercases_name_abbreviated(self):
        program = Program.objects.new_program(self.white_label.code, "SNAP")
        program.refresh_from_db()
        self.assertEqual(program.name_abbreviated, "snap")

    def test_save_lowercases_mixed_case_on_update(self):
        program = Program.objects.new_program(self.white_label.code, "snap")
        program.name_abbreviated = "Co_Snap"
        program.save()
        program.refresh_from_db()
        self.assertEqual(program.name_abbreviated, "co_snap")

    def test_save_leaves_already_lowercase_unchanged(self):
        program = Program.objects.new_program(self.white_label.code, "tx_snap")
        program.refresh_from_db()
        self.assertEqual(program.name_abbreviated, "tx_snap")
