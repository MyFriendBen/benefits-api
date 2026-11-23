"""NC Work First input tests."""

from django.test import SimpleTestCase, TestCase

from programs.framework.pe_dependencies import member as member_dependency
from programs.framework.pe_dependencies import spm as spm_dependency
from programs.programs.cross_white_label.tanf.nc import NcTanf
from programs.programs.testing_fixtures.households import add_income, add_member, make_screen

UnearnedTotal = spm_dependency.NcTanfCountableGrossUnearnedIncomeDependency
EarnedThroughPe = member_dependency.SelfEmploymentWithRentalAndBoarderIncomeDependency


class TestNcTanfInputs(SimpleTestCase):
    def test_pe_name_is_nc_tanf(self):
        self.assertEqual(NcTanf.pe_name, "nc_tanf")

    def test_earned_aggregate_is_not_sent(self):
        # Sending it switches off PE's NC exclusions (children's earnings, SSI recipients' income,
        # 27.5% of gross earnings).
        fields = {Data.field for Data in NcTanf.pe_inputs}
        self.assertNotIn("nc_tanf_countable_earned_income", fields)

    def test_earned_income_is_sent_per_member(self):
        self.assertIn(member_dependency.EmploymentIncomeDependency, NcTanf.pe_inputs)
        self.assertIn(EarnedThroughPe, NcTanf.pe_inputs)

    def test_unearned_total_is_sent(self):
        self.assertIn(UnearnedTotal, NcTanf.pe_inputs)

    def test_no_two_inputs_write_the_same_field(self):
        # A program declaring two classes for one field with different values is dropped.
        fields = [Data.field for Data in NcTanf.pe_inputs if getattr(Data, "field", None)]
        self.assertEqual(len(fields), len(set(fields)))

    def test_unearned_sources_are_not_also_sent_per_member(self):
        # The total replaces PE's own sum, so per-member unearned inputs would have no effect.
        for Data in (
            member_dependency.RentalIncomeDependency,
            member_dependency.PensionIncomeDependency,
            member_dependency.SocialSecurityIncomeDependency,
            member_dependency.AlimonyIncomeDependency,
            member_dependency.ChildSupportReceivedDependency,
            member_dependency.MiscellaneousIncomeDependency,
        ):
            self.assertNotIn(Data, NcTanf.pe_inputs)


class NcIncomeTestCase(TestCase):
    def setUp(self):
        self.screen = make_screen("nc", "NC", household_size=3)
        self.parent = add_member(self.screen, "headOfHousehold", 30)
        self.child = add_member(self.screen, "child", 8)

    def unearned_total(self):
        return UnearnedTotal(self.screen, [], {}).value()

    def earned_through_pe(self, member):
        return EarnedThroughPe(self.screen, member, {}).value()


class TestNcUnearnedTotal(NcIncomeTestCase):
    def test_counts_each_type_wf_114_counts(self):
        # Every type here is "Yes / Unearned" in WF-114, or the nearest row for it. The first four
        # are the ones PolicyEngine's own NC list leaves out.
        for income_type in (
            "investment",
            "deferredComp",
            "workersComp",
            "veteran",
            "pension",
            "sSDisability",
            "sSRetirement",
            "unemployment",
            "alimony",
            "childSupport",
        ):
            with self.subTest(income_type=income_type):
                self.parent.income_streams.all().delete()
                add_income(self.parent, 100, income_type, "monthly")
                self.assertEqual(self.unearned_total(), 1_200)

    def test_leaves_out_earned_income(self):
        for income_type in ("wages", "selfEmployment", "rental", "boarder"):
            with self.subTest(income_type=income_type):
                self.parent.income_streams.all().delete()
                add_income(self.parent, 100, income_type, "monthly")
                self.assertEqual(self.unearned_total(), 0)

    def test_leaves_out_types_wf_114_does_not_count(self):
        for income_type in ("sSI", "cashAssistance", "cashAssistanceOther", "gifts"):
            with self.subTest(income_type=income_type):
                self.parent.income_streams.all().delete()
                add_income(self.parent, 100, income_type, "monthly")
                self.assertEqual(self.unearned_total(), 0)

    def test_leaves_out_everything_an_ssi_recipient_receives(self):
        add_income(self.parent, 900, "sSI", "monthly")
        add_income(self.parent, 200, "pension", "monthly")
        self.assertEqual(self.unearned_total(), 0)

    def test_an_ssi_recipient_does_not_exclude_another_members_income(self):
        add_income(self.parent, 900, "sSI", "monthly")
        add_income(self.parent, 200, "pension", "monthly")
        other = add_member(self.screen, "spouse", 32)
        add_income(other, 100, "pension", "monthly")
        self.assertEqual(self.unearned_total(), 1_200)

    def test_counts_a_childs_unearned_income(self):
        # WF-114: a child's unearned income counts, their earned income does not.
        add_income(self.child, 100, "childSupport", "monthly")
        self.assertEqual(self.unearned_total(), 1_200)

    def test_sums_across_members_and_frequencies(self):
        add_income(self.parent, 100, "pension", "monthly")
        add_income(self.child, 1_200, "childSupport", "yearly")
        self.assertEqual(self.unearned_total(), 2_400)


class TestNcEarnedThroughPe(NcIncomeTestCase):
    def test_sends_self_employment_rental_and_boarder_as_earned(self):
        add_income(self.parent, 100, "selfEmployment", "monthly")
        add_income(self.parent, 50, "rental", "monthly")
        add_income(self.parent, 25, "boarder", "monthly")
        self.assertEqual(self.earned_through_pe(self.parent), 2_100)

    def test_does_not_send_unearned_types(self):
        add_income(self.parent, 100, "pension", "monthly")
        add_income(self.parent, 100, "investment", "monthly")
        self.assertEqual(self.earned_through_pe(self.parent), 0)

    def test_every_counted_type_reaches_exactly_one_bucket(self):
        # Earned types reach PE and are absent from the total, so nothing counts twice or not at all.
        for income_type in ("selfEmployment", "rental", "boarder", "pension", "investment", "workersComp"):
            with self.subTest(income_type=income_type):
                self.parent.income_streams.all().delete()
                add_income(self.parent, 100, income_type, "monthly")
                self.assertEqual(self.earned_through_pe(self.parent) + self.unearned_total(), 1_200)
