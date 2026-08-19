"""
Payload and wiring tests for ``MoPts`` / ``mo_pts`` — the Missouri Property Tax Credit
("Circuit Breaker").

These assert what *we* send PolicyEngine and how the calculator is registered, by
inspecting the request rather than calling out. The spec's Test Scenarios 1–22 are
asserted end to end against PolicyEngine in
``programs/programs/mo/pts/tests/test_mo_pts.py``, one VCR integration test per scenario.

The split is deliberate. Six inputs depart from the usual set, each because a shared
dependency delivers the right dollars to a PolicyEngine variable this formula does not
read. A scenario test catches that as a wrong dollar amount; the tests here catch it as
the wrong request, which is the level a regression is actually diagnosable at. Every one
was verified load-bearing by removing it and re-running the affected scenarios live:

===========================================  =======================  =================
Variant                                      Scenario                 Result
===========================================  =======================  =================
as implemented                               6, 12, 13, 17, 22        all match spec
``veterans_benefits`` mapping, no flag       13 / 22                  $0 / $272
flag set, veteran income -> pension          13 / 22                  $0 / $272
neither                                      13 / 22                  $0 / $272
``AgeDependency`` (screening-date age)       6                        ineligible, $0
no ``social_security_survivors`` component   12                       ineligible, $0
reported-SSI channel instead of ``ssi``      17                       $1,178 (want $1,069)
===========================================  =======================  =================

The $272 row is why the scenario tests assert value and not eligibility alone: that
household comes back *eligible* with an amount wrong by $828.
"""

import datetime
from unittest.mock import Mock

from django.test import TestCase

import programs.framework.pe_dependencies as dependency
from integrations.clients.policyengine.registry import all_calculators
from programs.framework.pe_base import PolicyEngineTaxUnitCalulator
from programs.framework.pe_dependencies.payload import pe_input
from programs.models import WhiteLabel
from screener.models import Expense, HouseholdMember, IncomeStream, Screen
from programs.programs.white_labels.mo.pts.calculator import MoPts

PERIOD = "2026"
CLAIM_YEAR = 2026


class MoPtsScenarioTestCase(TestCase):
    """Builds the household a spec scenario describes and inspects the PolicyEngine
    request it produces."""

    @classmethod
    def setUpTestData(cls):
        cls.white_label = WhiteLabel.objects.create(name="Missouri", code="mo", state_code="MO")

    def build_screen(self, people, housing_situation, expense_type=None, expense_amount=None):
        screen = Screen.objects.create(
            white_label=self.white_label,
            zipcode="65101",
            county="Cole County",
            household_size=len(people),
            household_assets=0,
            housing_situation=housing_situation,
            completed=False,
        )
        for person in people:
            birth_year, birth_month = person["birth"]
            member = HouseholdMember.objects.create(
                screen=screen,
                relationship=person["relationship"],
                birth_year_month=datetime.date(birth_year, birth_month, 1),
                age=CLAIM_YEAR - birth_year,
                disabled=person.get("disabled", False),
                long_term_disability=False,
                visually_impaired=False,
                veteran=person.get("veteran", False),
                student=False,
                pregnant=False,
            )
            for income_type, amount in (person.get("incomes") or {}).items():
                IncomeStream.objects.create(
                    screen=screen,
                    household_member=member,
                    type=income_type,
                    amount=amount,
                    frequency="yearly",
                )
        if expense_type is not None:
            Expense.objects.create(
                screen=screen,
                household_member=screen.household_members.first(),
                type=expense_type,
                amount=expense_amount,
                frequency="yearly",
            )
        return screen

    def payload(self, screen):
        program = Mock()
        program.year.period = PERIOD
        calculator = MoPts(screen, program, screen.missing_fields())
        return pe_input(screen, [calculator])

    def people_values(self, screen, field):
        """The value of ``field`` sent for each person, keyed by member id."""
        people = self.payload(screen)["household"]["people"]
        return {member_id: person.get(field, {}).get(PERIOD) for member_id, person in people.items()}


class TestWiring(MoPtsScenarioTestCase):
    """Registration and class shape."""

    def test_registered_under_config_name_abbreviated(self):
        """``screener.views`` resolves calculators by ``Program.name_abbreviated``, so the
        code the class declares must equal the ``mo_pts`` in
        ``mo_pts_initial_config.json`` or the program silently returns no value.

        Asserted against the built registry rather than the class attribute so the walk
        that has to find the class is exercised too.
        """
        self.assertEqual(MoPts.program_code, "mo_pts")
        self.assertIs(all_calculators["mo_pts"], MoPts)

    def test_is_tax_unit_calculator(self):
        self.assertTrue(issubclass(MoPts, PolicyEngineTaxUnitCalulator))

    def test_reads_mo_property_tax_credit(self):
        self.assertEqual(MoPts.pe_name, "mo_property_tax_credit")

    def test_reads_the_credit_amount(self):
        self.assertEqual(MoPts.pe_outputs, [dependency.tax.MoPropertyTaxCredit])

    def test_sends_mo_state_code(self):
        screen = self.build_screen(
            [{"birth": (1954, 1), "relationship": "headOfHousehold", "incomes": {"pension": 10_800}}],
            "renting",
            "rent",
            6_000,
        )
        household = self.payload(screen)["household"]["households"]["household"]
        self.assertIn("MO", household["state_code"].values())


class TestZeroCreditIsNotSurfaced(MoPtsScenarioTestCase):
    """A $0 credit is reported ineligible, which is what the results page shows anyway.

    PolicyEngine models eligibility (``mo_ptc_taxunit_eligible``) separately from the
    amount, and a household can satisfy every gate while the phaseout floors the credit at
    $0 (spec Benefit Value item 8). We deliberately do not read that flag: the frontend
    requires ``program.eligible && programValue(program) > 0`` to show a program, so
    surfacing "eligible for $0" would be filtered identically while inviting a filing that
    pays nothing.
    """

    def test_uses_the_base_class_value_derived_eligibility(self):
        """No ``eligible()`` override — the inherited ``value > 0`` is the intended rule."""
        self.assertIs(MoPts.eligible, PolicyEngineTaxUnitCalulator.eligible)

    def test_does_not_request_the_eligibility_flag(self):
        screen = self.build_screen(
            [{"birth": (1954, 1), "relationship": "headOfHousehold", "incomes": {"pension": 37_900}}],
            "renting",
            "rent",
            600,
        )
        tax_unit = self.payload(screen)["household"]["tax_units"]["main_tax_unit"]
        self.assertNotIn("mo_ptc_taxunit_eligible", tax_unit)


class TestVeteranIncomeRouting(MoPtsScenarioTestCase):
    """Veteran income reaches ``veterans_benefits``, and the exclusion's gating flag is set."""

    def veteran_screen(self, relationship):
        people = [{"birth": (1970, 1), "relationship": "headOfHousehold", "incomes": {}}]
        person = {
            "birth": (1975, 1),
            "relationship": relationship,
            "incomes": {"veteran": 46_800},
            "disabled": True,
            "veteran": True,
        }
        if relationship == "headOfHousehold":
            people = [person]
        else:
            people.append(person)
        return self.build_screen(people, "homeowner", "propertyTax", 1_100)

    def test_veteran_income_is_sent_as_veterans_benefits(self):
        """``mo_ptc_gross_income`` subtracts ``veterans_benefits``; the same dollars sent as
        ``taxable_pension_income`` reach the formula via ``mo_adjusted_gross_income``, where
        the exclusion cannot see them."""
        screen = self.veteran_screen("headOfHousehold")
        self.assertIn(46_800, self.people_values(screen, "veterans_benefits").values())

    def test_veteran_income_is_not_double_counted_as_pension(self):
        """``PensionIncomeWithoutVeteranDependency`` holds the stream back from
        ``taxable_pension_income`` so it is counted once."""
        screen = self.veteran_screen("headOfHousehold")
        self.assertEqual(set(self.people_values(screen, "taxable_pension_income").values()), {0})

    def test_service_connected_flag_is_set_for_a_disabled_veteran(self):
        """PolicyEngine defines no formula for
        ``is_fully_disabled_service_connected_veteran``, so the exclusion never fires
        unless we send it."""
        screen = self.veteran_screen("headOfHousehold")
        flags = self.people_values(screen, "is_fully_disabled_service_connected_veteran")
        self.assertIn(True, flags.values())

    def test_service_connected_flag_is_set_on_the_spouse_side(self):
        screen = self.veteran_screen("spouse")
        flags = self.people_values(screen, "is_fully_disabled_service_connected_veteran")
        self.assertIn(True, flags.values())

    def test_flag_is_false_without_veteran_income(self):
        """The proxy reads the ``veteran`` income stream, not ``HouseholdMember.veteran``,
        which the frontend never populates."""
        screen = self.build_screen(
            [
                {
                    "birth": (1970, 1),
                    "relationship": "headOfHousehold",
                    "incomes": {"sSDisability": 10_800},
                    "disabled": True,
                    "veteran": True,
                }
            ],
            "renting",
            "rent",
            4_800,
        )
        flags = self.people_values(screen, "is_fully_disabled_service_connected_veteran")
        self.assertEqual(set(flags.values()), {False})

    def test_flag_is_false_for_a_veteran_who_is_not_disabled(self):
        screen = self.build_screen(
            [{"birth": (1970, 1), "relationship": "headOfHousehold", "incomes": {"veteran": 46_800}}],
            "homeowner",
            "propertyTax",
            1_100,
        )
        flags = self.people_values(screen, "is_fully_disabled_service_connected_veteran")
        self.assertEqual(set(flags.values()), {False})


class TestAgeIsMeasuredAtYearEnd(MoPtsScenarioTestCase):
    """Age comes from ``AgeAtEndOf2026Dependency``, not the screening date."""

    def test_uses_the_end_of_claim_year_age_dependency(self):
        self.assertIn(dependency.member.AgeAtEndOf2026Dependency, MoPts.pe_inputs)
        self.assertNotIn(dependency.member.AgeDependency, MoPts.pe_inputs)

    def test_claim_year_is_the_program_year(self):
        self.assertEqual(dependency.member.AgeAtEndOf2026Dependency.claim_year, CLAIM_YEAR)

    def test_later_in_year_birthday_reports_the_attained_age(self):
        """A September 1961 claimant attains 65 during 2026. ``AgeDependency`` would report
        64 when screened before September and fail the age pathway."""
        screen = self.build_screen(
            [{"birth": (1961, 9), "relationship": "headOfHousehold", "incomes": {"pension": 12_000}}],
            "homeowner",
            "propertyTax",
            1_200,
        )
        self.assertEqual(set(self.people_values(screen, "age").values()), {65})


class TestSurvivorBenefitsRouting(MoPtsScenarioTestCase):
    """Survivor benefits reach ``social_security_survivors``, not just the total."""

    def test_survivor_component_is_sent(self):
        """``social_security`` is a PolicyEngine ``adds`` aggregate: setting the total leaves
        every component at zero, and the survivor pathway reads the component."""
        screen = self.build_screen(
            [{"birth": (1966, 1), "relationship": "headOfHousehold", "incomes": {"sSSurvivor": 13_200}}],
            "renting",
            "rent",
            5_400,
        )
        self.assertIn(13_200, self.people_values(screen, "social_security_survivors").values())

    def test_survivor_total_is_still_sent(self):
        screen = self.build_screen(
            [{"birth": (1966, 1), "relationship": "headOfHousehold", "incomes": {"sSSurvivor": 13_200}}],
            "renting",
            "rent",
            5_400,
        )
        self.assertIn(13_200, self.people_values(screen, "social_security").values())

    def test_retirement_benefits_are_not_reported_as_survivor_benefits(self):
        screen = self.build_screen(
            [{"birth": (1954, 1), "relationship": "headOfHousehold", "incomes": {"sSRetirement": 14_400}}],
            "renting",
            "rent",
            6_000,
        )
        self.assertEqual(set(self.people_values(screen, "social_security_survivors").values()), {0})


class TestSsiRouting(MoPtsScenarioTestCase):
    """Reported SSI is sent as ``ssi``, the variable the income formula adds."""

    def test_sends_ssi_and_not_ssi_reported(self):
        """``mo_ptc_gross_income`` adds the ``ssi`` variable. The ``ssi_reported`` channel
        feeds only the deprecated ``applicable_ssi`` and moves nothing without
        ``use_reported_ssi``, so the credit would be computed off income that omits it.

        Asserted on the fields the request carries rather than on which dependency class
        is listed: the class that used to send ``ssi_reported`` no longer exists, but the
        field is what the formula reads either way.
        """
        self.assertIn(dependency.member.Ssi, MoPts.pe_inputs)

        fields = {input.field for input in MoPts.pe_inputs}
        self.assertIn("ssi", fields)
        self.assertNotIn("ssi_reported", fields)

    def test_reported_ssi_is_sent(self):
        screen = self.build_screen(
            [
                {"birth": (1958, 1), "relationship": "headOfHousehold", "incomes": {"sSRetirement": 14_400}},
                {"birth": (2015, 1), "relationship": "child", "incomes": {"sSI": 4_800}},
            ],
            "homeowner",
            "propertyTax",
            1_200,
        )
        self.assertIn(4_800, self.people_values(screen, "ssi").values())

    def test_unreported_ssi_is_left_for_policyengine_to_simulate(self):
        screen = self.build_screen(
            [{"birth": (1954, 1), "relationship": "headOfHousehold", "incomes": {"pension": 10_800}}],
            "renting",
            "rent",
            6_000,
        )
        self.assertEqual(set(self.people_values(screen, "ssi").values()), {None})


class TestQualifyingPaymentRouting(MoPtsScenarioTestCase):
    """Rent and property tax are person-level inputs on the filers."""

    def test_property_tax_is_sent_per_person(self):
        """``real_estate_taxes`` is a PolicyEngine Person variable; sending it on the
        household unit fails the request with an entity mismatch."""
        screen = self.build_screen(
            [{"birth": (1954, 1), "relationship": "headOfHousehold", "incomes": {"pension": 10_800}}],
            "homeowner",
            "propertyTax",
            1_500,
        )
        payload = self.payload(screen)
        self.assertIn(1_500, self.people_values(screen, "real_estate_taxes").values())
        self.assertNotIn("real_estate_taxes", payload["household"]["households"]["household"])

    def test_rent_is_sent_per_person(self):
        screen = self.build_screen(
            [{"birth": (1954, 1), "relationship": "headOfHousehold", "incomes": {"pension": 10_800}}],
            "renting",
            "rent",
            6_000,
        )
        self.assertIn(6_000, self.people_values(screen, "rent").values())

    def test_married_filers_split_the_payment(self):
        """PolicyEngine sums the tax unit's members, so a split preserves the total while
        keeping each filer's share on the filer."""
        screen = self.build_screen(
            [
                {"birth": (1958, 1), "relationship": "headOfHousehold", "incomes": {"sSRetirement": 31_200}},
                {"birth": (1960, 1), "relationship": "spouse", "incomes": {"sSRetirement": 22_600}},
            ],
            "homeowner",
            "propertyTax",
            1_700,
        )
        self.assertEqual(sum(self.people_values(screen, "real_estate_taxes").values()), 1_700)
