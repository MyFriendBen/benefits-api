"""Federal school lunch tests."""

from django.test import SimpleTestCase

from programs.framework.base import PaymentUnit
from programs.programs.cross_white_label.nslp.base import SchoolLunch
import programs.framework.pe_dependencies as dependency


class TestSchoolLunchWiring(SimpleTestCase):
    def test_pe_inputs_includes_age(self):
        """PE derives ``is_in_k12_school`` from age; without it there are no K-12 children
        to value and the subsidy collapses to $0."""
        self.assertIn(dependency.member.AgeDependency, SchoolLunch.pe_inputs)

    def test_pe_inputs_includes_school_meal_countable_income(self):
        """The tier is set by countable income; unsent, every household reads as $0 income
        and lands in the free tier."""
        self.assertIn(dependency.spm.SchoolMealCountableIncomeDependency, SchoolLunch.pe_inputs)

    def test_the_payment_unit_is_member(self):
        """The NSLP spec's section 7 says `member`; every state's PE calculator inherits it
        rather than the SPM base's household unit."""
        from integrations.clients.policyengine.registry import all_calculators
        from programs.programs import calculators

        school_lunch = {
            code: calculator.payment_unit
            for code, calculator in {**calculators, **all_calculators}.items()
            if issubclass(calculator, SchoolLunch)
        }

        self.assertEqual(set(school_lunch), {"nslp", "il_nslp", "ks_nslp", "mo_nslp", "nc_nslp", "tx_nslp"})
        self.assertEqual(set(school_lunch.values()), {PaymentUnit.MEMBER})
