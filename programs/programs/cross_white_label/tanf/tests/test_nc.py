"""NC Work First input tests."""

from django.test import SimpleTestCase

from programs.framework.pe_dependencies import member as member_dependency
from programs.framework.pe_dependencies import spm as spm_dependency
from programs.programs.cross_white_label.tanf.nc import NcTanf


class TestNcTanfInputs(SimpleTestCase):
    def test_pe_name_is_nc_tanf(self):
        self.assertEqual(NcTanf.pe_name, "nc_tanf")

    def test_countable_income_aggregates_are_not_sent(self):
        # Sending either one switches off PE's NC exclusions (children's earnings, SSI
        # recipients' income, 27.5% of gross earnings).
        fields = {Data.field for Data in NcTanf.pe_inputs}
        self.assertNotIn("nc_tanf_countable_earned_income", fields)
        self.assertNotIn("nc_tanf_countable_gross_unearned_income", fields)
        self.assertFalse(hasattr(spm_dependency, "NcTanfCountableEarnedIncomeDependency"))

    def test_per_member_income_is_sent_so_pe_can_compute_countable_income(self):
        for Data in [
            member_dependency.EmploymentIncomeDependency,
            member_dependency.SelfEmploymentIncomeDependency,
            member_dependency.AlimonyIncomeDependency,
            member_dependency.ChildSupportReceivedDependency,
        ]:
            self.assertIn(Data, NcTanf.pe_inputs)

    def test_gifts_stay_excluded(self):
        self.assertNotIn(member_dependency.MiscellaneousIncomeDependency, NcTanf.pe_inputs)
