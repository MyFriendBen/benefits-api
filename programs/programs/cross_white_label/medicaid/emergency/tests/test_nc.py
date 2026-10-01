"""NC Emergency Medicaid tests."""

from programs.programs.cross_white_label.medicaid.emergency.nc import NcEmergencyMedicaid
from programs.programs.testing_fixtures.custom_calculator import CustomCalculatorTestCase, eligible_result


class TestNcEmergencyMedicaid(CustomCalculatorTestCase):
    calculator_class = NcEmergencyMedicaid
    program_code = "nc_emergency_medicaid"
    white_label_code = "nc"
    state_code = "NC"
    stores_age = False

    def eligible_ages(self, *ages):
        screen = self.make_screen(household_size=len(ages))
        for i, age in enumerate(ages):
            self.add_member(screen, "headOfHousehold" if i == 0 else "spouse", age)

        e = self.calculate(screen, data={"nc_medicaid": eligible_result()})

        return e, sorted(m.member.calc_age() for m in e.eligible_members if m.eligible)

    def test_max_age_is_inclusive(self):
        """Adults are covered through age 64; Medicare starts at 65."""
        for age, expected in [(63, [63]), (64, [64]), (65, [])]:
            with self.subTest(age=age):
                _, eligible = self.eligible_ages(age)
                self.assertEqual(eligible, expected)

    def test_value_counts_each_eligible_member(self):
        e, eligible = self.eligible_ages(64, 65)

        self.assertEqual(eligible, [64])
        self.assertEqual(e.value, NcEmergencyMedicaid.member_amount)
