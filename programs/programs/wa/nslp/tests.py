from decimal import Decimal

from django.test import TestCase

from programs.models import Program, FederalPoveryLimit
from programs.programs.calc import MemberEligibility
from programs.programs.wa import wa_calculators
from programs.programs.wa.nslp.calculator import WaNslp
from programs.util import Dependencies
from screener.models import HouseholdMember, IncomeStream, Screen, WhiteLabel


class TestWaNslp(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Washington", code="wa", state_code="WA")
        cls.fpl_year = FederalPoveryLimit.objects.create(year="2025", period="2025")
        cls.program = Program.objects.new_program(white_label="wa", name_abbreviated="wa_nslp")
        cls.program.year = cls.fpl_year
        cls.program.save()

    def _calc(self, screen: Screen) -> WaNslp:
        return WaNslp(screen, self.program, {}, Dependencies())

    def _screen_base(self, **kwargs) -> Screen:
        defaults = dict(
            white_label=self.white_label,
            agree_to_tos=True,
            completed=False,
            household_size=3,
            has_nslp=False,
            has_snap=False,
            has_tanf=False,
            has_head_start=False,
            has_early_head_start=False,
            has_medicaid=False,
        )
        defaults.update(kwargs)
        return Screen.objects.create(**defaults)

    def test_registered(self):
        self.assertIn("wa_nslp", wa_calculators)
        self.assertIs(wa_calculators["wa_nslp"], WaNslp)

    def test_eligible_by_income_below_free_tier(self):
        """Spec / validation: HH 3, one school-age child, income below reduced cap."""
        screen = self._screen_base(zipcode="98101", county="King County")
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=36, has_income=True)
        IncomeStream.objects.create(
            screen=screen,
            household_member=screen.household_members.get(relationship="headOfHousehold"),
            type="wages",
            amount=2000,
            frequency="monthly",
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=34, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=7, has_income=False)

        result = self._calc(screen).calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_ineligible_monthly_income_cents_over_reduced_cap(self):
        """HH3 monthly cap $4,109 — cents must not be truncated (CodeRabbit / Decimal)."""
        screen = self._screen_base(zipcode="98103", county="King County", household_size=3)
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=39, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=Decimal("4109.99"), frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=37, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=12, has_income=False)

        result = self._calc(screen).calc()
        self.assertFalse(result.eligible)

    def test_ineligible_income_one_dollar_over_reduced_monthly(self):
        """$4,110/mo for HH3 — over $4,109 monthly reduced-price cap; Medicaid irrelevant."""
        screen = self._screen_base(
            zipcode="98103",
            county="King County",
            household_size=3,
            has_medicaid=True,
            has_benefits="true",
        )
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=39, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=4110, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=37, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=12, has_income=False)

        result = self._calc(screen).calc()
        self.assertFalse(result.eligible)

    def test_eligible_at_reduced_monthly_cap_exact(self):
        """Regression: frequency-matched monthly must not always annualize (+$5 error)."""
        screen = self._screen_base(zipcode="98103", county="King County")
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=39, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=4109, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=37, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=12, has_income=False)

        result = self._calc(screen).calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_eligible_snap_categorical_high_income(self):
        screen = self._screen_base(
            zipcode="99201",
            county="Spokane County",
            has_snap=True,
            has_benefits="true",
        )
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=40, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=7000, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=39, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=10, has_income=False)

        result = self._calc(screen).calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_eligible_tanf_categorical(self):
        screen = self._screen_base(zipcode="98901", county="Yakima County", has_tanf=True, has_benefits="true")
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=36, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=5500, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=35, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=9, has_income=False)

        result = self._calc(screen).calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_ineligible_snap_but_no_school_age_child(self):
        screen = self._screen_base(zipcode="98103", county="King County", household_size=2, has_snap=True)
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=40, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=1800, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="child", age=3, has_income=False)

        result = self._calc(screen).calc()
        self.assertFalse(result.eligible)

    def test_ineligible_already_has_nslp(self):
        screen = self._screen_base(has_nslp=True)
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=36, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=2000, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=34, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=7, has_income=False)

        result = self._calc(screen).calc()
        self.assertFalse(result.eligible)

    def test_eligible_early_head_start_flag_high_income(self):
        screen = self._screen_base(
            zipcode="98402",
            county="Pierce County",
            has_early_head_start=True,
            has_benefits="true",
        )
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=33, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=5000, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=32, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=5, has_income=False)

        result = self._calc(screen).calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_eligible_head_start_flag_high_income(self):
        screen = self._screen_base(
            zipcode="98402",
            county="Pierce County",
            has_head_start=True,
            has_benefits="true",
        )
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=33, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=5000, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=32, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=5, has_income=False)

        result = self._calc(screen).calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_snap_categorical_uses_presumed_eligibility_pass_message_not_income(self):
        screen = self._screen_base(
            zipcode="99201",
            county="Spokane County",
            has_snap=True,
            has_benefits="true",
        )
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=40, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=7000, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=39, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=10, has_income=False)

        result = self._calc(screen).calc()
        self.assertTrue(result.eligible)
        self.assertTrue(any("Presumed eligibility" in str(m) for m in result.pass_messages))
        self.assertFalse(any("Household makes" in str(m) for m in result.pass_messages))

    def test_eligible_foster_child_categorical(self):
        screen = self._screen_base(household_size=3)
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=35, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=8000, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=34, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="fosterChild", age=12, has_income=False)

        result = self._calc(screen).calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)

    def test_two_school_age_children_value_scales(self):
        screen = self._screen_base(zipcode="99201", county="Spokane County", household_size=6)
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=40, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=2400, frequency="monthly"
        )
        spouse = HouseholdMember.objects.create(screen=screen, relationship="spouse", age=38, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=spouse, type="wages", amount=800, frequency="monthly"
        )
        HouseholdMember.objects.create(screen=screen, relationship="child", age=15, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=11, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=6, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=2, has_income=False)

        result = self._calc(screen).calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828 * 3)

    def test_mixed_frequency_uses_annual_limit(self):
        screen = self._screen_base(household_size=3)
        head = HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=39, has_income=True)
        IncomeStream.objects.create(
            screen=screen, household_member=head, type="wages", amount=2000, frequency="monthly"
        )
        IncomeStream.objects.create(screen=screen, household_member=head, type="wages", amount=500, frequency="yearly")
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=37, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="child", age=12, has_income=False)

        calc = self._calc(screen)
        self.assertTrue(calc._income_at_or_below_reduced_cap())

    def test_member_eligible_false_for_head(self):
        calc = self._calc(self._screen_base())
        e = MemberEligibility(HouseholdMember(relationship="headOfHousehold", age=30))
        calc.member_eligible(e)
        self.assertFalse(e.eligible)

    def test_grandchild_counts(self):
        screen = self._screen_base(household_size=3)
        HouseholdMember.objects.create(screen=screen, relationship="headOfHousehold", age=55, has_income=True)
        IncomeStream.objects.create(
            screen=screen,
            household_member=screen.household_members.get(relationship="headOfHousehold"),
            type="wages",
            amount=2500,
            frequency="monthly",
        )
        HouseholdMember.objects.create(screen=screen, relationship="spouse", age=54, has_income=False)
        HouseholdMember.objects.create(screen=screen, relationship="grandChild", age=10, has_income=False)

        result = self._calc(screen).calc()
        self.assertTrue(result.eligible)
        self.assertEqual(result.value, 828)
