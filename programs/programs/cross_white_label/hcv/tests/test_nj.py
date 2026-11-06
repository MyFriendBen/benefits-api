"""
NJ Housing Choice Voucher (``NjHcv``): one test per scenario in the NJ spec's section 8, plus the
NJ values and the lookups NJ asks HUD for.

HUD's figures are the ones each scenario quotes, stubbed through ``hud_ami``: FY2026 low-income
limits and FY2027 FMRs or Small Area FMRs. Every HUD call is made by the base module, so the
stub patches ``HousingChoiceVoucher``'s module.

The spec states $0/month for scenarios 2 and 15, where the tenant payment exceeds the payment
standard. The calculator floors an eligible household at $1 a year so the results page still
shows it (the page hides a program worth $0), so those tests assert 1.
"""

from typing import Optional

from programs.programs.cross_white_label.hcv.base import HousingChoiceVoucher
from programs.programs.cross_white_label.hcv.nj import NjHcv
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase, hud_ami
from programs.framework.base import Eligibility
from screener.models import Screen

# FY2026 HUD low-income (80%) limits the scenarios quote.
NEWARK_LOW_INCOME = {1: 74_800, 2: 85_450, 3: 96_150, 4: 106_800}
MIDDLESEX_LOW_INCOME = {2: 91_700, 4: 114_600}
HUDSON_LOW_INCOME = {3: 106_150}

# FY2027 FMRs by bedrooms.
NEWARK_FMR = {0: 1_637, 1: 1_850, 2: 2_233}
MIDDLESEX_FMR = {1: 2_103, 2: 2_623}
HOBOKEN_07030_SAFMR = {2: 4_190}


class NjHcvTestCase(CustomCalculatorTestCase):
    calculator_class = NjHcv
    white_label_code = "nj"
    state_code = "NJ"
    fpl_year = "2026"
    default_zipcode = "07102"
    default_county = "Essex County"
    stores_age = False

    def run_scenario(
        self,
        screen: Screen,
        limit: int,
        payment_standard: Optional[int] = None,
        bedrooms: Optional[int] = None,
    ) -> Eligibility:
        """Run NjHcv with HUD answering `limit` for the 80% row and `payment_standard` for the
        voucher size, and check NJ asked for the right row, year and bedrooms."""
        with hud_ami(HousingChoiceVoucher, {"80%": limit}, payment_standard=payment_standard) as hud:
            e = self.calculate(screen)

        hud.get_screen_il_ami.assert_called_once_with(screen, "80%", "2026")
        if bedrooms is not None:
            hud.get_screen_payment_standard.assert_called_once_with(screen, bedrooms, 2027)
        return e

    def family_of_three(self, assets: int = 0, **screen_kwargs) -> Screen:
        screen = self.make_screen(household_size=3, household_assets=assets, **screen_kwargs)
        self.add_member(screen, "headOfHousehold", 35, monthly_income=2_000)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 5)
        return screen

    def single_adult(self, age: int = 40, yearly_income: int = 0, **member_kwargs) -> Screen:
        screen = self.make_screen(household_size=1)
        self.add_member(screen, "headOfHousehold", age, yearly_income=yearly_income, **member_kwargs)
        return screen

    def assert_eligible(self, e: Eligibility, monthly_value: int) -> None:
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, monthly_value * 12)


class TestNjHcvConfiguration(NjHcvTestCase):
    def test_program_code(self) -> None:
        self.assertEqual(NjHcv.program_code, "nj_hcv")

    def test_nj_values(self) -> None:
        self.assertEqual(NjHcv.net_assets_limit_amount, 109_797)
        self.assertEqual(NjHcv.student_earnings_cap, 525)
        self.assertEqual(NjHcv.dependent_deduction, 525)
        self.assertEqual(NjHcv.elderly_disabled_deduction, 575)
        self.assertEqual(NjHcv.minimum_rent, 0)
        self.assertEqual(NjHcv.payment_standard_year, 2027)
        self.assertTrue(NjHcv.special_category_assumed)

    def test_voucher_size_follows_dca_subsidy_standards(self) -> None:
        expected = {1: 0, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4}
        for household_size, bedrooms in expected.items():
            with self.subTest(household_size=household_size):
                screen = self.make_screen(household_size=household_size)
                self.assertEqual(self.make_calculator(screen).voucher_size(), bedrooms)

    def test_nj_safmr_metros_are_mandatory(self) -> None:
        from integrations.clients.hud_income_limits import hud_client

        for area in (
            "Bergen-Passaic, NJ HUD Metro FMR Area",
            "Jersey City, NJ HUD Metro FMR Area",
            "Monmouth-Ocean, NJ HUD Metro FMR Area",
            "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD MSA",
        ):
            self.assertIn(area, hud_client.MANDATORY_SAFMR_AREA_NAMES)
        self.assertNotIn("Newark, NJ HUD Metro FMR Area", hud_client.MANDATORY_SAFMR_AREA_NAMES)
        self.assertNotIn("Middlesex-Somerset-Hunterdon, NJ HUD Metro FMR Area", hud_client.MANDATORY_SAFMR_AREA_NAMES)


class TestNjHcvSpecScenarios(NjHcvTestCase):
    def test_scenario_01_family_of_three_in_essex(self) -> None:
        # 2BR $2,233 − round(30% × ($24,000 − 2 × $525) ÷ 12) = $574
        e = self.run_scenario(self.family_of_three(), NEWARK_LOW_INCOME[3], NEWARK_FMR[2], bedrooms=2)
        self.assert_eligible(e, 1_659)

    def test_scenario_02_single_adult_at_low_income_limit(self) -> None:
        # 0BR $1,637 − $1,870 is below $0; floored at $1 a year (spec: $0/month).
        e = self.run_scenario(self.single_adult(yearly_income=74_800), NEWARK_LOW_INCOME[1], NEWARK_FMR[0], 0)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1)

    def test_scenario_03_single_adult_one_dollar_over(self) -> None:
        e = self.run_scenario(self.single_adult(yearly_income=74_801), NEWARK_LOW_INCOME[1])
        self.assertFalse(e.eligible)

    def test_scenario_04_between_50_and_80_percent(self) -> None:
        # Above the $48,450 very-low-income limit; admitted on the 80% route.
        e = self.run_scenario(self.single_adult(yearly_income=60_000), NEWARK_LOW_INCOME[1], NEWARK_FMR[0], 0)
        self.assert_eligible(e, 137)

    def test_scenario_05_assets_at_limit(self) -> None:
        e = self.run_scenario(self.family_of_three(assets=109_797), NEWARK_LOW_INCOME[3], NEWARK_FMR[2], 2)
        self.assert_eligible(e, 1_659)

    def test_scenario_06_assets_one_dollar_over(self) -> None:
        e = self.run_scenario(self.family_of_three(assets=109_798), NEWARK_LOW_INCOME[3])
        self.assertFalse(e.eligible)

    def test_scenario_07_student_23_living_alone(self) -> None:
        screen = self.single_adult(age=23, yearly_income=10_000, student=True, student_full_time=True)
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[1])
        self.assertFalse(e.eligible)

    def test_scenario_08_student_24_living_alone(self) -> None:
        screen = self.single_adult(age=24, yearly_income=10_000, student=True, student_full_time=True)
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[1], NEWARK_FMR[0], 0)
        self.assert_eligible(e, 1_387)

    def test_scenario_09_head_aged_17(self) -> None:
        e = self.run_scenario(self.single_adult(age=17, yearly_income=10_000), NEWARK_LOW_INCOME[1])
        self.assertFalse(e.eligible)

    def test_scenario_10_head_aged_18(self) -> None:
        e = self.run_scenario(self.single_adult(age=18, yearly_income=10_000), NEWARK_LOW_INCOME[1], NEWARK_FMR[0], 0)
        self.assert_eligible(e, 1_387)

    def test_scenario_11_senior_62_with_medical_bills(self) -> None:
        # 0BR $1,637 − round(30% × ($18,000 − $575 − ($3,000 − $1,800)) ÷ 12) = $406
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", 62, monthly_income=1_500, income_type="sSRetirement")
        self.add_expense(head, 3_000, "medical", "yearly")
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[1], NEWARK_FMR[0], 0)
        self.assert_eligible(e, 1_231)

    def test_scenario_12_child_care_with_a_12_year_old(self) -> None:
        # 2BR $2,233 − round(30% × ($24,000 − $1,050 − $3,600) ÷ 12) = $484
        screen = self.make_screen(household_size=3)
        head = self.add_member(screen, "headOfHousehold", 35, monthly_income=2_000)
        self.add_member(screen, "child", 12)
        self.add_member(screen, "child", 14)
        self.add_expense(head, 300, "childCare")
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[3], NEWARK_FMR[2], 2)
        self.assert_eligible(e, 1_749)

    def test_scenario_13_hoboken_small_area_rent(self) -> None:
        # 07030's 2BR Small Area FMR $4,190 − $574
        screen = self.family_of_three(zipcode="07030", county="Hudson County")
        e = self.run_scenario(screen, HUDSON_LOW_INCOME[3], HOBOKEN_07030_SAFMR[2], 2)
        self.assert_eligible(e, 3_616)

    def test_scenario_14_parent_and_teenager_in_middlesex(self) -> None:
        # 1BR $2,103 − round(30% × ($24,000 − $525) ÷ 12) = $587; the 17-year-old's wages don't count.
        screen = self.make_screen(household_size=2, zipcode="08901", county="Middlesex County")
        self.add_member(screen, "headOfHousehold", 40, monthly_income=2_000)
        self.add_member(screen, "child", 17, monthly_income=500)
        e = self.run_scenario(screen, MIDDLESEX_LOW_INCOME[2], MIDDLESEX_FMR[1], 1)
        self.assert_eligible(e, 1_516)

    def family_of_four_in_middlesex(self, yearly_income: int) -> Screen:
        screen = self.make_screen(household_size=4, zipcode="08901", county="Middlesex County")
        self.add_member(screen, "headOfHousehold", 40, yearly_income=yearly_income)
        self.add_member(screen, "spouse", 38)
        self.add_member(screen, "child", 8)
        self.add_member(screen, "child", 5)
        return screen

    def test_scenario_15_family_of_four_at_middlesex_limit(self) -> None:
        # 2BR $2,623 − $2,839 is below $0; floored at $1 a year (spec: $0/month).
        screen = self.family_of_four_in_middlesex(114_600)
        e = self.run_scenario(screen, MIDDLESEX_LOW_INCOME[4], MIDDLESEX_FMR[2], 2)
        self.assertTrue(e.eligible)
        self.assertEqual(e.value, 1)

    def test_scenario_16_family_of_four_one_dollar_over(self) -> None:
        e = self.run_scenario(self.family_of_four_in_middlesex(114_601), MIDDLESEX_LOW_INCOME[4])
        self.assertFalse(e.eligible)

    def test_scenario_17_married_student_aged_21(self) -> None:
        # 1BR $1,850 − round(30% × ($10,000 + $8,000) ÷ 12) = $450
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 21, yearly_income=10_000, student=True, student_full_time=True)
        self.add_member(screen, "spouse", 22, yearly_income=8_000)
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[2], NEWARK_FMR[1], 1)
        self.assert_eligible(e, 1_400)

    def test_scenario_18_student_aged_20_living_with_a_parent(self) -> None:
        # 1BR $1,850 − round(30% × ($24,000 + $525 − $525) ÷ 12) = $600
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 45, monthly_income=2_000)
        self.add_member(screen, "child", 20, monthly_income=500, student=True, student_full_time=True)
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[2], NEWARK_FMR[1], 1)
        self.assert_eligible(e, 1_250)

    def test_scenario_19_student_aged_22_with_a_child(self) -> None:
        # 1BR $1,850 − round(30% × ($12,000 − $525) ÷ 12) = $287
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 22, monthly_income=1_000, student=True, student_full_time=True)
        self.add_member(screen, "child", 3)
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[2], NEWARK_FMR[1], 1)
        self.assert_eligible(e, 1_563)

    def senior_on_social_security(self, age: int, medical_per_year: int) -> Screen:
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", age, monthly_income=1_500, income_type="sSRetirement")
        self.add_expense(head, medical_per_year, "medical", "yearly")
        return screen

    def test_scenario_20_medical_bills_below_threshold(self) -> None:
        # 0BR $1,637 − round(30% × ($18,000 − $575) ÷ 12) = $436
        e = self.run_scenario(self.senior_on_social_security(65, 1_000), NEWARK_LOW_INCOME[1], NEWARK_FMR[0], 0)
        self.assert_eligible(e, 1_201)

    def test_scenario_21_ten_percent_of_income_floor(self) -> None:
        # 0BR $1,637 − max(round(30% × $4,225 ÷ 12) = $106, 10% × $18,000 ÷ 12 = $150) = $1,487
        e = self.run_scenario(self.senior_on_social_security(70, 15_000), NEWARK_LOW_INCOME[1], NEWARK_FMR[0], 0)
        self.assert_eligible(e, 1_487)

    def test_scenario_22_adult_aged_61_with_medical_bills(self) -> None:
        # 0BR $1,637 − round(30% × $18,000 ÷ 12) = $450
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", 61, monthly_income=1_500)
        self.add_expense(head, 3_000, "medical", "yearly")
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[1], NEWARK_FMR[0], 0)
        self.assert_eligible(e, 1_187)

    def test_scenario_23_child_care_for_a_13_year_old(self) -> None:
        # 1BR $1,850 − round(30% × ($24,000 − $525) ÷ 12) = $587
        screen = self.make_screen(household_size=2)
        head = self.add_member(screen, "headOfHousehold", 35, monthly_income=2_000)
        self.add_member(screen, "child", 13)
        self.add_expense(head, 300, "childCare")
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[2], NEWARK_FMR[1], 1)
        self.assert_eligible(e, 1_263)

    def test_scenario_24_adult_aged_40_with_a_disability(self) -> None:
        # 0BR $1,637 − round(30% × ($18,000 − $575 − ($3,000 − $1,800)) ÷ 12) = $406
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", 40, monthly_income=1_500, disabled=True)
        self.add_expense(head, 3_000, "medical", "yearly")
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[1], NEWARK_FMR[0], 0)
        self.assert_eligible(e, 1_231)

    def test_scenario_25_parent_and_18_year_old_earner(self) -> None:
        # 1BR $1,850 − round(30% × ($24,000 + $6,000) ÷ 12) = $750
        screen = self.make_screen(household_size=2)
        self.add_member(screen, "headOfHousehold", 45, monthly_income=2_000)
        self.add_member(screen, "child", 18, monthly_income=500)
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[2], NEWARK_FMR[1], 1)
        self.assert_eligible(e, 1_100)


class TestNjHcvHeadOfHousehold(NjHcvTestCase):
    def test_head_age_unknown_is_not_barred(self) -> None:
        screen = self.make_screen(household_size=1)
        head = self.add_member(screen, "headOfHousehold", 40, yearly_income=10_000)
        self.set_age(head, None)
        e = self.run_scenario(screen, NEWARK_LOW_INCOME[1], NEWARK_FMR[0], 0)
        self.assert_eligible(e, 1_387)

    def test_minor_who_is_not_the_head_does_not_fail_the_rule(self) -> None:
        e = self.run_scenario(self.family_of_three(), NEWARK_LOW_INCOME[3], NEWARK_FMR[2], 2)
        self.assertTrue(e.eligible)
