"""
Spec-scenario tests for MO WFTC — one test per Test Scenario in ``spec.md``.

``MoWftc`` is a thin wrapper around PolicyEngine's ``mo_wftc``, so these assert the
whole credit end to end: the eligibility gate, the year-specific rate, the liability
cap net of the property tax credit, and the smaller-of result. Each runs the
scenario's household through PolicyEngine once and replays from a cassette.

Every scenario states a birth month and year rather than an age, and the reference date is
pinned to February 1 after the tax year, when a household screens to file it. ``MoWftc``
sends age on December 31 of the tax year. Members are born in June unless a scenario says
otherwise, so for them that equals the screening-date age; Scenario 19 is the one where the
two differ.

Scenario 15 is the one place PolicyEngine and Missouri's own test diverge, and its
expectation deliberately encodes PolicyEngine's answer — see ``spec.md`` criterion 5.
"""

import datetime
from unittest.mock import patch

from programs.programs.testing_fixtures.pe_integration import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)
from screener.models import Expense, HouseholdMember, Screen
from programs.programs.white_labels.mo.wftc.calculator import MoWftc
from programs.framework.pe_dependencies import member

PE_VERSION = "2.9.0"
BIRTH_MONTH = 6


class MoWftcScenarioTestCase(PeIntegrationTestCase):
    """Shared household builder. Every scenario is Cole County, ZIP 65101."""

    pe_version = PE_VERSION

    # Distinct per subclass so each scenario's cassette pins its own household.
    screen_id = 0
    tax_year = "2025"

    def setUp(self):
        super().setUp()
        reference_date = patch.object(
            Screen, "get_reference_date", return_value=datetime.date(int(self.tax_year) + 1, 2, 1)
        )
        reference_date.start()
        self.addCleanup(reference_date.stop)

    def build(self, household_size):
        # make_screen creates the white label; make_program looks it up, so it
        # has to run second.
        screen = make_screen(
            self.screen_id,
            white_label_code="mo",
            state_code="MO",
            household_size=household_size,
            zipcode="65101",
            county="Cole County",
        )
        self.program = make_program("mo", "mo_wftc", self.tax_year)
        return screen

    def add_person(self, screen, offset, relationship, birth_year, birth_month=BIRTH_MONTH, **kwargs):
        """A member born in ``birth_month`` of ``birth_year``; ``age`` is still set because the model requires it."""
        reference_date = Screen.get_reference_date(screen)
        return add_member(
            screen,
            self.screen_id * 10 + offset,
            relationship,
            HouseholdMember.age_from_date(datetime.date(birth_year, birth_month, 1), reference_date),
            birth_year_month=datetime.date(birth_year, birth_month, 1),
            **kwargs,
        )

    def run_wftc(self, screen):
        return calc_pe_program(screen, MoWftc, self.program)

    def add_property_tax(self, member, amount):
        """Annual real estate taxes paid, feeding PolicyEngine's ``real_estate_taxes``."""
        return self.add_housing_expense(member, "propertyTax", amount)

    def add_rent(self, member, amount):
        """Annual rent, feeding PolicyEngine's ``rent``."""
        return self.add_housing_expense(member, "rent", amount)

    def add_housing_expense(self, member, expense_type, amount):
        return Expense.objects.create(
            screen=member.screen,
            household_member=member,
            type=expense_type,
            amount=amount,
            frequency="yearly",
        )

    def hoh_and_child(self, screen, wages=40_000, extra=None):
        """The spec's base household: one HOH born 1990 with wages, one child born 2015 with no income."""
        hoh = self.add_person(screen, 1, "headOfHousehold", 1990)
        add_income(hoh, wages, "wages", "yearly")
        if extra:
            income_type, amount = extra
            add_income(hoh, amount, income_type, "yearly")
        self.add_person(screen, 2, "child", 2015)
        return hoh


class TestScenario01GoldenPath(MoWftcScenarioTestCase):
    """HOH golden path, uncapped credit → eligible, $333."""

    screen_id = 9101

    def test_eligible_at_full_twenty_percent(self):
        screen = self.build(2)
        self.hoh_and_child(screen)
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 333)


class TestScenario02TaxYear2023Rate(MoWftcScenarioTestCase):
    """Year-parameter guard: at TY2023 the 10% rate applies rather than 20% → eligible, $104.

    Not a reachable outcome — the program has one configured year. This proves the wrapper
    reads the rate for the year it is sent rather than hard-coding one.
    """

    screen_id = 9102
    tax_year = "2023"

    def test_uses_ten_percent_rate(self):
        screen = self.build(2)
        self.hoh_and_child(screen)
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 104)


class TestScenario03InvestmentOverLimit(MoWftcScenarioTestCase):
    """$6,000 investment income exceeds the $4,400 limit → not eligible."""

    screen_id = 9103

    def test_investment_income_disqualifies(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("investment", 6_000))
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario04NoRemainingLiability(MoWftcScenarioTestCase):
    """The credit is capped at remaining Missouri liability, which is $0 here.

    The gate passes and the potential credit is positive; the cap is what zeroes it.
    """

    screen_id = 9104

    def test_zero_liability_means_not_eligible(self):
        screen = self.build(2)
        self.hoh_and_child(screen, wages=25_000)
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario05CappedCredit(MoWftcScenarioTestCase):
    """Remaining liability is below 20% of the federal EITC, so it binds → $292."""

    screen_id = 9105

    def test_liability_cap_binds(self):
        screen = self.build(2)
        self.hoh_and_child(screen, wages=35_000)
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 292)


class TestScenario06FederalEitcPhasedOut(MoWftcScenarioTestCase):
    """No federal EITC means no Missouri credit to piggyback on → not eligible."""

    screen_id = 9106

    def test_no_federal_eitc_means_not_eligible(self):
        screen = self.build(2)
        self.hoh_and_child(screen, wages=55_000)
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario07InvestmentAtThreshold(MoWftcScenarioTestCase):
    """Exactly $4,400 is at the threshold, not over it → eligible, $192."""

    screen_id = 9107

    def test_exactly_at_threshold_stays_eligible(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("investment", 4_400))
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 192)


class TestScenario08InvestmentOneOverThreshold(MoWftcScenarioTestCase):
    """$4,401 is one dollar over the threshold → not eligible."""

    screen_id = 9108

    def test_one_dollar_over_disqualifies(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("investment", 4_401))
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario09InvestmentAtThreshold2023(MoWftcScenarioTestCase):
    """Year-parameter guard: TY2023's threshold is $4,050, and exactly that stays eligible → $40."""

    screen_id = 9109
    tax_year = "2023"

    def test_exactly_at_2023_threshold_stays_eligible(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("investment", 4_050))
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 40)


class TestScenario10InvestmentAtThreshold2024(MoWftcScenarioTestCase):
    """Year-parameter guard: TY2024's threshold is $4,300, and exactly that stays eligible → $152."""

    screen_id = 9110
    tax_year = "2024"

    def test_exactly_at_2024_threshold_stays_eligible(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("investment", 4_300))
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 152)


class TestScenario11InvestmentOneOverThreshold2024(MoWftcScenarioTestCase):
    """Year-parameter guard: $4,301 is one dollar over the TY2024 threshold → not eligible."""

    screen_id = 9111
    tax_year = "2024"

    def test_one_dollar_over_2024_threshold_disqualifies(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("investment", 4_301))
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario12SingleChildlessWorker(MoWftcScenarioTestCase):
    """A childless filer gets the much smaller childless federal EITC → $16."""

    screen_id = 9112

    def test_childless_filer_eligible_for_small_credit(self):
        screen = self.build(1)
        hoh = self.add_person(screen, 1, "headOfHousehold", 1995)
        add_income(hoh, 18_000, "wages", "yearly")
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 16)


class TestScenario13MarriedFilingCombined(MoWftcScenarioTestCase):
    """A spouse present produces the Joint treatment → eligible, $401."""

    screen_id = 9113

    def test_joint_household_eligible(self):
        screen = self.build(3)
        hoh = self.add_person(screen, 1, "headOfHousehold", 1990)
        add_income(hoh, 45_000, "wages", "yearly")
        self.add_person(screen, 2, "spouse", 1990)
        self.add_person(screen, 3, "child", 2015)
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 401)


class TestScenario14PropertyTaxCreditAbsorbsLiability(MoWftcScenarioTestCase):
    """The property tax credit consumes all remaining liability → not eligible.

    Liability of $23.24 against a $149 property tax credit. Fails as eligible/$23 if
    ``real_estate_taxes`` is not sent.
    """

    screen_id = 9114

    def test_ptc_absorbs_liability(self):
        screen = self.build(2)
        hoh = self.add_person(screen, 1, "headOfHousehold", 1959)
        add_income(hoh, 29_500, "wages", "yearly")
        self.add_property_tax(hoh, 1_100)
        self.add_person(screen, 2, "child", 2015)
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario15RentalCountsTowardInvestmentGate(MoWftcScenarioTestCase):
    """Rental income counts toward the investment gate → not eligible.

    A rental-exempt gate would return $174 instead, so this is the test that
    detects one. See ``spec.md`` criterion 5 for why PolicyEngine's measure is
    the accepted one.
    """

    screen_id = 9115

    def test_rental_income_disqualifies(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("rental", 5_000))
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario16PropertyTaxCreditPartiallyReducesLiability(MoWftcScenarioTestCase):
    """The property tax credit reduces but does not exhaust liability → $11.

    Liability of $32.48 less a $21 property tax credit leaves $11.49, well below the
    uncapped credit. The household sits $100 of wages under the property tax credit's
    income ceiling rather than on it, so the credit doesn't vanish on a small change.
    """

    screen_id = 9116

    def test_positive_credit_survives_ptc(self):
        screen = self.build(2)
        hoh = self.add_person(screen, 1, "headOfHousehold", 1959)
        add_income(hoh, 29_900, "wages", "yearly")
        self.add_property_tax(hoh, 1_000)
        self.add_person(screen, 2, "child", 2015)
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 11)


class TestScenario17RenterPropertyTaxCreditAbsorbsLiability(MoWftcScenarioTestCase):
    """Year-parameter guard: at TY2026 a senior renter's property tax credit consumes all
    remaining liability → not eligible.

    Liability of $101.72 against a $385 property tax credit computed from rent. Fails as
    eligible/$101 if ``rent`` is not sent. At TY2025 rent cannot change the result, since a
    renter's credit phases out before Missouri liability turns positive; TY2026 becomes the
    tax year on January 1, 2027, and there it can.
    """

    screen_id = 9117
    tax_year = "2026"

    def test_rent_based_ptc_absorbs_liability(self):
        screen = self.build(2)
        hoh = self.add_person(screen, 1, "headOfHousehold", 1959)
        add_income(hoh, 33_000, "wages", "yearly")
        self.add_rent(hoh, 12_000)
        self.add_person(screen, 2, "child", 2015)
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario18FullTimeStudentChild(MoWftcScenarioTestCase):
    """A 20-year-old full-time student is a qualifying child → eligible, $285."""

    screen_id = 9118

    def test_student_child_qualifies(self):
        screen = self.build(2)
        hoh = self.add_person(screen, 1, "headOfHousehold", 1990)
        add_income(hoh, 35_000, "wages", "yearly")
        self.add_person(screen, 2, "child", 2005, student=True, student_full_time=True)
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 285)


class TestScenario19ChildTurned19AfterTheTaxYear(MoWftcScenarioTestCase):
    """A child who was 18 on December 31 is a qualifying child for that year → eligible, $285.

    Born January 2007, so 19 by the February screening date. Fails as not eligible if the
    screening-date age is sent.
    """

    screen_id = 9119

    def test_age_is_measured_at_end_of_tax_year(self):
        screen = self.build(2)
        hoh = self.add_person(screen, 1, "headOfHousehold", 1990)
        add_income(hoh, 35_000, "wages", "yearly")
        self.add_person(screen, 2, "child", 2007, birth_month=1, student=False)
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 285)
