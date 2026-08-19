"""
Spec-scenario tests for MO PTS — one test per Test Scenario in ``spec.md``.

``MoPts`` supplies inputs and reads PolicyEngine's ``mo_property_tax_credit``, so these
assert the whole credit end to end: the qualifying pathways, the four filing-status and
ownership income limits, the phaseout, and both statutory caps. Each runs the scenario's
household through PolicyEngine once and replays from a cassette.

Every scenario states a birth month and year rather than an age. That is load-bearing:
the statute measures age on December 31 of the claim year, so ``MoPts`` sends
``AgeAtEndOf2026Dependency`` instead of the screening-date age. Scenario 6 fails without
it.

Scenario 19 is the one place a scenario's expected screener result departs from its
statutory result. The household satisfies every eligibility gate and the phaseout floors
the credit at $0; because a $0 program is never displayed, the expected result is
ineligible rather than "eligible, $0" — see ``spec.md`` Scenario 19.
"""

import datetime

from programs.framework.tests.integration_test_helpers import (
    PeIntegrationTestCase,
    add_income,
    add_member,
    calc_pe_program,
    make_program,
    make_screen,
    screener_value,
)
from screener.models import Expense
from programs.programs.white_labels.mo.pts.calculator import MoPts

PE_VERSION = "1.786.5"
CLAIM_YEAR = 2026


class MoPtsScenarioTestCase(PeIntegrationTestCase):
    """Shared household builder. Every scenario is Cole County, ZIP 65101."""

    pe_version = PE_VERSION

    # Distinct per subclass so each scenario's cassette pins its own household.
    screen_id = 0
    tax_year = "2026"

    def build(self, household_size, housing_situation):
        # make_screen creates the white label; make_program looks it up, so it
        # has to run second.
        screen = make_screen(
            self.screen_id,
            white_label_code="mo",
            state_code="MO",
            household_size=household_size,
            zipcode="65101",
            county="Cole County",
            housing_situation=housing_situation,
        )
        self.program = make_program("mo", "mo_pts", self.tax_year)
        return screen

    def run_pts(self, screen):
        return calc_pe_program(screen, MoPts, self.program)

    def add_person(self, screen, offset, relationship, birth_year, birth_month, disabled=False):
        """A member identified by birth month/year, as every scenario states them.

        ``age`` is still set because the model requires it, but ``MoPts`` reads the
        end-of-year age off ``birth_year_month``.
        """
        return add_member(
            screen,
            self.screen_id * 10 + offset,
            relationship,
            CLAIM_YEAR - birth_year,
            birth_year_month=datetime.date(birth_year, birth_month, 1),
            disabled=disabled,
            long_term_disability=False,
        )

    def add_housing_expense(self, member, expense_type, amount):
        """Annual rent or property tax, feeding ``rent`` / ``real_estate_taxes``."""
        return Expense.objects.create(
            screen=member.screen,
            household_member=member,
            type=expense_type,
            amount=amount,
            frequency="yearly",
        )

    def assert_result(self, screen, expected_eligible, expected_value):
        result = self.run_pts(screen)
        self.assertEqual(
            (bool(result.eligible), screener_value(result)),
            (expected_eligible, expected_value),
        )


class TestScenario01GoldenPathSeniorRenter(MoPtsScenarioTestCase):
    """Baseline age-65 pathway, renter homestead → eligible, $1,033."""

    screen_id = 8201

    def test_eligible_at_the_top_renter_band(self):
        screen = self.build(1, "renting")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1954, 1)
        add_income(hoh, 14_400, "sSRetirement", "yearly")
        self.add_housing_expense(hoh, "rent", 6_000)
        self.assert_result(screen, True, 1_033)


class TestScenario02SingleRenterAtTheLimit(MoPtsScenarioTestCase):
    """Single renter exactly at the $38,200 limit → eligible, $280."""

    screen_id = 8202

    def test_eligible_at_the_income_boundary(self):
        screen = self.build(1, "renting")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1958, 1)
        add_income(hoh, 38_200, "pension", "yearly")
        self.add_housing_expense(hoh, "rent", 9_000)
        self.assert_result(screen, True, 280)


class TestScenario03SingleHomeownerAtTheLimit(MoPtsScenarioTestCase):
    """Single homeowner exactly at the $42,200 limit → eligible, $695."""

    screen_id = 8203

    def test_eligible_at_the_owner_income_boundary(self):
        screen = self.build(1, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1958, 1)
        add_income(hoh, 42_200, "pension", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_800)
        self.assert_result(screen, True, 695)


class TestScenario04SingleRenterOverTheLimit(MoPtsScenarioTestCase):
    """One dollar over the $38,200 limit → not eligible."""

    screen_id = 8204

    def test_one_dollar_over_disqualifies(self):
        screen = self.build(1, "renting")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1954, 1)
        add_income(hoh, 38_201, "pension", "yearly")
        self.add_housing_expense(hoh, "rent", 6_000)
        self.assert_result(screen, False, 0)


class TestScenario05AtTheMinimumBase(MoPtsScenarioTestCase):
    """Age exactly 65, income exactly at the $14,300 base → no phaseout, eligible, $1,500."""

    screen_id = 8205

    def test_no_phaseout_at_or_below_the_base(self):
        screen = self.build(1, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1961, 1)
        add_income(hoh, 14_300, "pension", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_500)
        self.assert_result(screen, True, 1_500)


class TestScenario06TurnsSixtyFiveLaterInTheYear(MoPtsScenarioTestCase):
    """Born September 1961 — age is measured on Dec 31, not the screening date.

    The case that requires ``AgeAtEndOf2026Dependency``: the screening-date age reads 64
    for most of the year and fails the age-65 pathway.
    """

    screen_id = 8206

    def test_end_of_year_age_qualifies(self):
        screen = self.build(1, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1961, 9)
        add_income(hoh, 12_000, "pension", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_200)
        self.assert_result(screen, True, 1_200)


class TestScenario07NoHomestead(MoPtsScenarioTestCase):
    """Neither owns nor rents → not eligible."""

    screen_id = 8207

    def test_no_homestead_disqualifies(self):
        screen = self.build(1, "otherWithoutSubsidy")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1954, 1)
        add_income(hoh, 10_800, "pension", "yearly")
        self.assert_result(screen, False, 0)


class TestScenario08AdultChildIncomeExcluded(MoPtsScenarioTestCase):
    """An adult child's income is outside the assistance unit → eligible, $1,550 (owner cap)."""

    screen_id = 8208

    def test_adult_child_income_is_excluded(self):
        screen = self.build(3, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1956, 1)
        add_income(hoh, 10_800, "sSRetirement", "yearly")
        spouse = self.add_person(screen, 2, "spouse", 1958, 1)
        add_income(spouse, 8_400, "sSRetirement", "yearly")
        child = self.add_person(screen, 3, "child", 1987, 1)
        add_income(child, 3_000, "wages", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 2_200)
        self.assert_result(screen, True, 1_550)


class TestScenario09MarriedHomeownersOverTheLimit(MoPtsScenarioTestCase):
    """Married full-year homeowners over the $48,000 limit → not eligible."""

    screen_id = 8209

    def test_over_the_married_owner_limit(self):
        screen = self.build(2, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1955, 1)
        add_income(hoh, 22_800, "sSRetirement", "yearly")
        add_income(hoh, 18_000, "pension", "yearly")
        spouse = self.add_person(screen, 2, "spouse", 1957, 1)
        add_income(spouse, 9_600, "sSRetirement", "yearly")
        add_income(spouse, 3_600, "pension", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 2_500)
        self.assert_result(screen, False, 0)


class TestScenario10ClaimantDisabilityPathway(MoPtsScenarioTestCase):
    """Under 65 and disabled → eligible, $960."""

    screen_id = 8210

    def test_disability_pathway_qualifies(self):
        screen = self.build(1, "renting")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1970, 1, disabled=True)
        add_income(hoh, 10_800, "sSDisability", "yearly")
        self.add_housing_expense(hoh, "rent", 4_800)
        self.assert_result(screen, True, 960)


class TestScenario11NoQualifyingPathway(MoPtsScenarioTestCase):
    """Turns 65 the following year, not disabled or a veteran → not eligible."""

    screen_id = 8211

    def test_no_pathway_disqualifies(self):
        screen = self.build(1, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1962, 1)
        add_income(hoh, 12_000, "pension", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_400)
        self.assert_result(screen, False, 0)


class TestScenario12ClaimantSurvivorPathway(MoPtsScenarioTestCase):
    """Age 60 on survivor benefits → eligible, $1,055 (renter cap).

    The case that requires ``SocialSecuritySurvivorsIncomeDependency``: the survivor test
    reads ``social_security_survivors``, which stays at zero if only the total is sent.
    """

    screen_id = 8212

    def test_survivor_pathway_qualifies(self):
        screen = self.build(1, "renting")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1966, 1)
        add_income(hoh, 13_200, "sSSurvivor", "yearly")
        self.add_housing_expense(hoh, "rent", 5_400)
        self.assert_result(screen, True, 1_055)


class TestScenario13ClaimantVeteranBenefitsExcluded(MoPtsScenarioTestCase):
    """VA disability compensation excluded from PTC income → eligible, $1,100.

    The case that requires both ``VeteransBenefitsDependency`` and
    ``IsFullyDisabledServiceConnectedVeteranDependency``; either alone returns $0.
    """

    screen_id = 8213

    def test_veterans_benefits_are_excluded(self):
        screen = self.build(1, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1975, 1, disabled=True)
        add_income(hoh, 46_800, "veteran", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_100)
        self.assert_result(screen, True, 1_100)


class TestScenario14MarriedRenterAtTheLimit(MoPtsScenarioTestCase):
    """Married renters at the $41,000 limit → eligible, $227."""

    screen_id = 8214

    def test_eligible_at_the_married_renter_boundary(self):
        screen = self.build(2, "renting")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1958, 1)
        add_income(hoh, 16_800, "sSRetirement", "yearly")
        spouse = self.add_person(screen, 2, "spouse", 1960, 1)
        add_income(spouse, 14_400, "sSRetirement", "yearly")
        add_income(spouse, 12_600, "pension", "yearly")
        self.add_housing_expense(hoh, "rent", 7_200)
        self.assert_result(screen, True, 227)


class TestScenario15SpouseOnlyAgePathway(MoPtsScenarioTestCase):
    """The spouse satisfies the age pathway → eligible, $1,474."""

    screen_id = 8215

    def test_spouse_age_qualifies_the_household(self):
        screen = self.build(2, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1970, 1)
        add_income(hoh, 9_600, "pension", "yearly")
        spouse = self.add_person(screen, 2, "spouse", 1958, 1)
        add_income(spouse, 13_200, "sSRetirement", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_700)
        self.assert_result(screen, True, 1_474)


class TestScenario16SpouseSurvivorDoesNotQualifyClaimant(MoPtsScenarioTestCase):
    """The survivor pathway is claimant-only → not eligible.

    Unlike the age and disability pathways, D does not pass through the spouse.
    """

    screen_id = 8216

    def test_survivor_pathway_does_not_pass_through_the_spouse(self):
        screen = self.build(2, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1978, 1)
        spouse = self.add_person(screen, 2, "spouse", 1966, 1)
        add_income(spouse, 12_000, "sSSurvivor", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_500)
        self.assert_result(screen, False, 0)


class TestScenario17MinorChildIncomeIncluded(MoPtsScenarioTestCase):
    """A minor child's SSI counts in PTC income → eligible, $1,069.

    The case that requires the ``ssi`` input: reported SSI reaches
    ``mo_ptc_gross_income`` only as ``ssi``, and the credit is $1,178 without it.
    """

    screen_id = 8217

    def test_minor_child_ssi_is_counted(self):
        screen = self.build(2, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1958, 1)
        add_income(hoh, 14_400, "sSRetirement", "yearly")
        child = self.add_person(screen, 2, "child", 2015, 1)
        add_income(child, 4_800, "sSI", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_200)
        self.assert_result(screen, True, 1_069)


class TestScenario18ZeroQualifyingPayment(MoPtsScenarioTestCase):
    """No property tax paid → nothing to credit, not eligible."""

    screen_id = 8218

    def test_zero_payment_disqualifies(self):
        screen = self.build(1, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1954, 1)
        add_income(hoh, 10_800, "pension", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 0)
        self.assert_result(screen, False, 0)


class TestScenario19ZeroFloorIsNotSurfaced(MoPtsScenarioTestCase):
    """The phaseout exceeds the rent equivalent, flooring the credit at $0.

    PolicyEngine reports this household eligible — the $0 is a phaseout outcome, not an
    exclusion. ``MoPts`` keeps the inherited ``value > 0`` rule, so it reports ineligible:
    a $0 program is filtered from results either way, and "you qualify for $0" would
    invite a filing that pays nothing. See ``spec.md`` Scenario 19.
    """

    screen_id = 8219

    def test_zero_credit_reports_ineligible(self):
        screen = self.build(1, "renting")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1954, 1)
        add_income(hoh, 37_900, "pension", "yearly")
        self.add_housing_expense(hoh, "rent", 600)
        self.assert_result(screen, False, 0)


class TestScenario20SpouseDisabilityPathway(MoPtsScenarioTestCase):
    """The spouse satisfies the disability pathway → eligible, $1,474."""

    screen_id = 8220

    def test_spouse_disability_qualifies_the_household(self):
        screen = self.build(2, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1970, 1)
        add_income(hoh, 9_600, "pension", "yearly")
        spouse = self.add_person(screen, 2, "spouse", 1970, 1, disabled=True)
        add_income(spouse, 13_200, "sSDisability", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_700)
        self.assert_result(screen, True, 1_474)


class TestScenario21MarriedHomeownersAtTheLimit(MoPtsScenarioTestCase):
    """Married full-year homeowners exactly at the $48,000 limit → eligible, $578."""

    screen_id = 8221

    def test_eligible_at_the_married_owner_boundary(self):
        screen = self.build(2, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1958, 1)
        add_income(hoh, 31_200, "sSRetirement", "yearly")
        spouse = self.add_person(screen, 2, "spouse", 1960, 1)
        add_income(spouse, 22_600, "sSRetirement", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_700)
        self.assert_result(screen, True, 578)


class TestScenario22SpouseVeteranBenefitsExcluded(MoPtsScenarioTestCase):
    """The spouse's VA compensation is excluded → eligible, $1,100.

    The veteran exclusion applies on the spouse side too. This is the household that
    returns $272 — eligible, but wrong by $828 — with only one of the two veteran inputs.
    """

    screen_id = 8222

    def test_spouse_veterans_benefits_are_excluded(self):
        screen = self.build(2, "homeowner")
        hoh = self.add_person(screen, 1, "headOfHousehold", 1970, 1)
        spouse = self.add_person(screen, 2, "spouse", 1975, 1, disabled=True)
        add_income(spouse, 46_800, "veteran", "yearly")
        self.add_housing_expense(hoh, "propertyTax", 1_100)
        self.assert_result(screen, True, 1_100)
