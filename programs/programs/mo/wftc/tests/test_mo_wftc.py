"""
Spec-scenario tests for MO WFTC — one test per Test Scenario in ``spec.md``.

``MoWftc`` is a thin wrapper around PolicyEngine's ``mo_wftc``, so these assert the
whole credit end to end: the eligibility gate, the year-specific rate, the liability
cap net of the property tax credit, and the smaller-of result. Each runs the
scenario's household through PolicyEngine once and replays from a cassette.

Scenario 15 is the one place PolicyEngine and Missouri's own test diverge, and its
expectation deliberately encodes PolicyEngine's answer — see ``spec.md`` criterion 5.
"""

from programs.framework.tests.integration_test_helpers import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)
from programs.programs.mo.pe.tax import MoWftc
from screener.models import Expense

PE_VERSION = "1.786.5"


class MoWftcScenarioTestCase(PeIntegrationTestCase):
    """Shared household builder. Every scenario is Cole County, ZIP 65101."""

    pe_version = PE_VERSION

    # Distinct per subclass so each scenario's cassette pins its own household.
    screen_id = 0
    tax_year = "2025"

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

    def run_wftc(self, screen):
        return calc_pe_program(screen, MoWftc, self.program)

    def add_property_tax(self, member, amount):
        """Annual real estate taxes paid, which feed PolicyEngine's ``real_estate_taxes``.

        No harness helper exists for expenses, and the property tax credit cannot be
        computed without this — scenarios 14 and 16 turn on it.
        """
        return Expense.objects.create(
            screen=member.screen,
            household_member=member,
            type="propertyTax",
            amount=amount,
            frequency="yearly",
        )

    def hoh_and_child(self, screen, hoh_age=35, child_age=10, wages=40_000, extra=None):
        """The spec's base household: one HOH with wages, one child with no income."""
        hoh = add_member(screen, self.screen_id * 10 + 1, "headOfHousehold", hoh_age)
        add_income(hoh, wages, "wages", "yearly")
        if extra:
            income_type, amount = extra
            add_income(hoh, amount, income_type, "yearly")
        add_member(screen, self.screen_id * 10 + 2, "child", child_age)
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
    """TY2023 applies the 10% rate rather than 20% → eligible, $105."""

    screen_id = 9102
    tax_year = "2023"

    def test_uses_ten_percent_rate(self):
        screen = self.build(2)
        self.hoh_and_child(screen, hoh_age=33, child_age=8)
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 104)


class TestScenario03InvestmentOverLimit(MoWftcScenarioTestCase):
    """$6,000 investment income exceeds the TY2025 limit → not eligible."""

    screen_id = 9103

    def test_investment_income_disqualifies(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("investment", 6_000))
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario04NoRemainingLiability(MoWftcScenarioTestCase):
    """The credit is capped at remaining Missouri liability, which is $0 here.

    PolicyEngine's ``mo_wftc_eligible`` is True and ``mo_wftc_potential`` is positive;
    the liability cap is what zeroes the credit. Eligibility follows the value.
    """

    screen_id = 9104

    def test_zero_liability_means_not_eligible(self):
        screen = self.build(2)
        self.hoh_and_child(screen, wages=25_000)
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario05CappedCredit(MoWftcScenarioTestCase):
    """Remaining liability is below 20% of the federal EITC, so it binds → $293."""

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
    """Exactly $4,400 is at the TY2025 threshold, not over it → eligible, $193."""

    screen_id = 9107

    def test_exactly_at_threshold_stays_eligible(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("investment", 4_400))
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 192)


class TestScenario08InvestmentOneOverThreshold(MoWftcScenarioTestCase):
    """$4,401 is one dollar over the TY2025 threshold → not eligible."""

    screen_id = 9108

    def test_one_dollar_over_disqualifies(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("investment", 4_401))
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario09InvestmentAtThreshold2023(MoWftcScenarioTestCase):
    """TY2023's threshold is $4,050, and exactly that stays eligible → $40."""

    screen_id = 9109
    tax_year = "2023"

    def test_exactly_at_2023_threshold_stays_eligible(self):
        screen = self.build(2)
        self.hoh_and_child(screen, hoh_age=33, child_age=8, extra=("investment", 4_050))
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 40)


class TestScenario10InvestmentAtThreshold2024(MoWftcScenarioTestCase):
    """TY2024's threshold is $4,300, and exactly that stays eligible → $153."""

    screen_id = 9110
    tax_year = "2024"

    def test_exactly_at_2024_threshold_stays_eligible(self):
        screen = self.build(2)
        self.hoh_and_child(screen, hoh_age=34, child_age=9, extra=("investment", 4_300))
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 152)


class TestScenario11InvestmentOneOverThreshold2024(MoWftcScenarioTestCase):
    """$4,301 is one dollar over the TY2024 threshold → not eligible."""

    screen_id = 9111
    tax_year = "2024"

    def test_one_dollar_over_2024_threshold_disqualifies(self):
        screen = self.build(2)
        self.hoh_and_child(screen, hoh_age=34, child_age=9, extra=("investment", 4_301))
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario12SingleChildlessWorker(MoWftcScenarioTestCase):
    """A childless filer gets the much smaller childless federal EITC → $17."""

    screen_id = 9112

    def test_childless_filer_eligible_for_small_credit(self):
        screen = self.build(1)
        hoh = add_member(screen, 91121, "headOfHousehold", 30)
        add_income(hoh, 18_000, "wages", "yearly")
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 16)


class TestScenario13MarriedFilingCombined(MoWftcScenarioTestCase):
    """A spouse present produces the Joint treatment → eligible, $401."""

    screen_id = 9113

    def test_joint_household_eligible(self):
        screen = self.build(3)
        hoh = add_member(screen, 91131, "headOfHousehold", 35)
        add_income(hoh, 45_000, "wages", "yearly")
        add_member(screen, 91132, "spouse", 34)
        add_member(screen, 91133, "child", 10)
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 401)


class TestScenario14PropertyTaxCreditAbsorbsLiability(MoWftcScenarioTestCase):
    """The property tax credit consumes all remaining liability → not eligible.

    Confirms the WFTC cap is computed *after* the property tax credit, per Form
    MO-WFTC Lines 7-9.
    """

    screen_id = 9114

    def test_ptc_absorbs_liability(self):
        screen = self.build(2)
        hoh = add_member(screen, 91141, "headOfHousehold", 66)
        add_income(hoh, 28_400, "wages", "yearly")
        self.add_property_tax(hoh, 1_200)
        add_member(screen, 91142, "child", 10)
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario15RentalCountsTowardInvestmentGate(MoWftcScenarioTestCase):
    """Rental income counts toward the investment gate → not eligible.

    The one intentional divergence from Missouri's own test. Missouri routes filers
    with rental income to Pub. 596 Worksheet 1, which the screener cannot reconstruct
    from a single coarse rental total; PolicyEngine substitutes
    ``eitc_relevant_investment_income``, which counts rental dollar-for-dollar. We
    accept PolicyEngine's approximation rather than override the gate, so a household
    with $5,000 of rental income is excluded even though its true Worksheet 1 result
    might have cleared the threshold. See ``spec.md`` criterion 5.

    A calculator applying a rental-exempt four-component gate would return $174 here,
    so this test is what detects that behavior.
    """

    screen_id = 9115

    def test_rental_income_disqualifies(self):
        screen = self.build(2)
        self.hoh_and_child(screen, extra=("rental", 5_000))
        result = self.run_wftc(screen)
        self.assertFalse(result.eligible)


class TestScenario16PropertyTaxCreditPartiallyReducesLiability(MoWftcScenarioTestCase):
    """The property tax credit reduces but does not exhaust liability → $15."""

    screen_id = 9116

    def test_positive_credit_survives_ptc(self):
        screen = self.build(2)
        hoh = add_member(screen, 91161, "headOfHousehold", 66)
        add_income(hoh, 30_000, "wages", "yearly")
        self.add_property_tax(hoh, 1_010)
        add_member(screen, 91162, "child", 10)
        result = self.run_wftc(screen)
        self.assertTrue(result.eligible)
        self.assertEqual(screener_value(result), 14)
