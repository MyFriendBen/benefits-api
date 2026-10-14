"""
NJ FamilyCare Cover All Kids.

A plain custom calculator, so these build real Screen/HouseholdMember/IncomeStream rows and
run the real `calc()` — the tax unit comes from `HouseholdMember.is_in_tax_unit()`, which a
Mock would only restate. Every spec.md §8 scenario has a test named for it; the rest cover
each branch of the dependent filing test and the MAGI income exclusions.

Immigration status has no test: it lives on the program row's `legal_status_required`
(spec.md §4 `immigration_status_any`).
"""

from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase
from programs.programs.white_labels.nj.cover_all_kids.calculator import NjCoverAllKids
from programs.util import DependencyError
from screener.models import HouseholdMember, IncomeStream, Screen

PER_CHILD = 3_915


class NjCoverAllKidsTestCase(CustomCalculatorTestCase):
    calculator_class = NjCoverAllKids
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "07102"
    default_county = "Essex County"

    def family(self, head_wages: int = 0, children: tuple[int, ...] = (8, 12)) -> tuple[Screen, list[HouseholdMember]]:
        """Head, spouse with no income, and children of the given ages."""
        screen = self.make_screen(household_size=2 + len(children))
        head = self.add_member(screen, "headOfHousehold", 40, monthly_income=head_wages)
        self.add_member(screen, "spouse", 39)
        kids = [self.add_member(screen, "child", age) for age in children]

        return screen, [head, *kids]

    def eligible_ids(self, e) -> set[int]:
        return {m.member.id for m in e.eligible_members if m.eligible}


class TestRegistration(NjCoverAllKidsTestCase):
    def test_program_code(self):
        self.assertEqual(NjCoverAllKids.program_code, "nj_cover_all_kids")

    def test_missing_income_field_drops_the_program(self):
        screen, (head, *_) = self.family()
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=None, frequency="monthly"
        )

        with self.assertRaises(DependencyError):
            self.calculate(screen, missing=screen.missing_fields())


class TestSpecScenarios(NjCoverAllKidsTestCase):
    def test_1_two_young_children_moderate_wages(self):
        screen = self.make_screen(household_size=4)
        self.add_member(screen, "headOfHousehold", 35, monthly_income=5_000)
        self.add_member(screen, "spouse", 34)
        newborn = self.add_member(screen, "child", 0)
        ten = self.add_member(screen, "child", 10)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.eligible_ids(e), {newborn.id, ten.id})
        self.assertEqual(e.value, PER_CHILD * 2)

    def test_2_one_dollar_under_the_family_of_four_limit(self):
        screen, _ = self.family(head_wages=9_762)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, PER_CHILD * 2)

    def test_3_one_dollar_over_the_family_of_four_limit(self):
        screen, _ = self.family(head_wages=9_764)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_4_eighteen_year_old_qualifies(self):
        screen = self.make_screen(household_size=4)
        self.add_member(screen, "headOfHousehold", 45, monthly_income=3_000)
        self.add_member(screen, "spouse", 44)
        eighteen = self.add_member(screen, "child", 18)
        self.add_member(screen, "child", 25)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(self.eligible_ids(e), {eighteen.id})
        self.assertEqual(e.value, PER_CHILD)

    def test_5_nineteen_year_old_does_not(self):
        screen = self.make_screen(household_size=4)
        self.add_member(screen, "headOfHousehold", 45, monthly_income=3_000)
        self.add_member(screen, "spouse", 44)
        self.add_member(screen, "child", 19)
        self.add_member(screen, "child", 22)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)
        self.assertEqual(e.value, 0)

    def test_6_teen_summer_wages_under_filing_threshold_do_not_count(self):
        screen = self.make_screen(household_size=4)
        self.add_member(screen, "headOfHousehold", 40, monthly_income=9_000)
        self.add_member(screen, "spouse", 39)
        self.add_member(screen, "child", 16, monthly_income=800)
        self.add_member(screen, "child", 10)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, PER_CHILD * 2)

    def test_7_teen_who_must_file_pushes_family_over(self):
        screen = self.make_screen(household_size=4)
        self.add_member(screen, "headOfHousehold", 40, monthly_income=9_000)
        self.add_member(screen, "spouse", 39)
        self.add_member(screen, "child", 17, monthly_income=1_500)
        self.add_member(screen, "child", 10)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)

    def test_8_child_support_does_not_count(self):
        screen = self.make_screen(household_size=4)
        head = self.add_member(screen, "headOfHousehold", 38, monthly_income=8_000)
        self.add_income(head, 2_000, "childSupport")
        self.add_member(screen, "spouse", 37)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 12)

        e = self.calculate(screen)

        self.assertTrue(e.eligible)
        self.assertEqual(e.value, PER_CHILD * 2)


class TestMagiExclusions(NjCoverAllKidsTestCase):
    """SSI, child support, gifts and workers' compensation leave household income; the rest stays."""

    def test_each_excluded_type_is_left_out(self):
        for income_type in ("sSI", "childSupport", "gifts", "workersComp"):
            with self.subTest(income_type=income_type):
                screen, (head, *_) = self.family(head_wages=8_000)
                self.add_income(head, 2_000, income_type)

                self.assertTrue(self.calculate(screen).eligible)

    def test_counted_unearned_income_is_included(self):
        screen, (head, *_) = self.family(head_wages=8_000)
        self.add_income(head, 2_000, "unemployment")

        self.assertFalse(self.calculate(screen).eligible)

    def test_spouse_income_always_counts(self):
        screen = self.make_screen(household_size=4)
        self.add_member(screen, "headOfHousehold", 40, monthly_income=5_000)
        self.add_member(screen, "spouse", 39, monthly_income=5_000)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 12)

        self.assertFalse(self.calculate(screen).eligible)


class TestLimitUsesTaxUnitSize(NjCoverAllKidsTestCase):
    def test_limit_reads_the_tax_unit_member_count(self):
        """A family of three: 355% of $27,320 is $96,986/year, or $8,082.17/month."""
        screen, _ = self.family(head_wages=8_082, children=(5,))
        self.assertTrue(self.calculate(screen).eligible)

        screen, _ = self.family(head_wages=8_083, children=(5,))
        self.assertFalse(self.calculate(screen).eligible)


class TestMemberAge(NjCoverAllKidsTestCase):
    def test_unknown_age_is_not_eligible(self):
        screen, (_, kid) = self.family(children=(8,))
        self.set_age(kid, None)

        e = self.calculate(screen)

        self.assertFalse(e.eligible)


class TestMustFile(NjCoverAllKidsTestCase):
    """Each branch of the single-dependent filing test, on 2026 amounts."""

    def must_file(self, *streams: tuple[int, str], age: int = 16, visually_impaired: bool = False) -> bool:
        screen = self.make_screen(household_size=3)
        self.add_member(screen, "headOfHousehold", 40)
        dependent = self.add_member(screen, "child", age, visually_impaired=visually_impaired)
        for amount, income_type in streams:
            self.add_income(dependent, amount, income_type, frequency="yearly")

        return self.make_calculator(screen)._must_file(dependent)

    def test_no_income(self):
        self.assertFalse(self.must_file())

    def test_unearned_threshold(self):
        self.assertFalse(self.must_file((1_350, "investment")))
        self.assertTrue(self.must_file((1_351, "investment")))

    def test_earned_threshold(self):
        self.assertFalse(self.must_file((16_100, "wages")))
        self.assertTrue(self.must_file((16_101, "wages")))

    def test_gross_threshold_mixes_earned_and_unearned(self):
        """$1,000 wages + $1,000 investment: under each separate test, over $1,000 + $450."""
        self.assertTrue(self.must_file((1_000, "wages"), (1_000, "investment")))
        self.assertFalse(self.must_file((1_000, "wages"), (450, "investment")))

    def test_gross_threshold_floor_is_1350(self):
        self.assertTrue(self.must_file((100, "wages"), (1_300, "investment")))

    def test_self_employment_400(self):
        self.assertFalse(self.must_file((399, "selfEmployment")))
        self.assertTrue(self.must_file((400, "selfEmployment")))

    def test_blind_raises_each_threshold(self):
        self.assertFalse(self.must_file((3_400, "investment"), visually_impaired=True))
        self.assertTrue(self.must_file((3_401, "investment"), visually_impaired=True))

    def test_aged_raises_each_threshold(self):
        self.assertFalse(self.must_file((18_150, "wages"), age=65))
        self.assertTrue(self.must_file((18_151, "wages"), age=65))

    def test_aged_and_blind_add_twice(self):
        self.assertFalse(self.must_file((5_450, "investment"), age=70, visually_impaired=True))
        self.assertTrue(self.must_file((5_451, "investment"), age=70, visually_impaired=True))

    def test_social_security_left_out_below_base_amount(self):
        self.assertFalse(self.must_file((12_000, "sSSurvivor")))

    def test_social_security_counts_above_base_amount(self):
        """Half of $20,000 plus $15,500 wages is $25,500, over $25,000, so the survivor
        benefit enters the test as unearned income."""
        self.assertTrue(self.must_file((20_000, "sSSurvivor"), (15_500, "wages")))
        self.assertFalse(self.must_file((20_000, "sSSurvivor"), (14_000, "wages")))

    def test_excluded_types_never_trigger_filing(self):
        self.assertFalse(self.must_file((10_000, "sSI"), (10_000, "childSupport")))

    def dependent_parent_family(self, pension: int) -> Screen:
        """Family of five whose $133,200/year head wages sit under 355% FPL ($137,314) alone.
        The 70-year-old parent stays a dependent below the $5,300 qualifying-relative limit."""
        screen = self.make_screen(household_size=5)
        self.add_member(screen, "headOfHousehold", 40, monthly_income=11_100)
        self.add_member(screen, "spouse", 39)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 12)
        self.add_member(screen, "parent", 70, yearly_income=pension, income_type="pension")

        return screen

    def test_dependent_who_must_file_adds_income(self):
        """$5,000 pension is over the $3,400 aged unearned threshold, so it counts."""
        self.assertFalse(self.calculate(self.dependent_parent_family(5_000)).eligible)

    def test_dependent_who_need_not_file_adds_nothing(self):
        self.assertTrue(self.calculate(self.dependent_parent_family(3_000)).eligible)
