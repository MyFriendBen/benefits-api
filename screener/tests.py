from django.test import TestCase
from screener.models import Screen, WhiteLabel


class ScreenTestCase(TestCase):
    def test_create_single_parent_two_children_household(self):
        screen = create_single_parent_two_children_household(annual_income=15000)
        self.assertTrue(isinstance(screen, Screen))


def create_default_household_member(screen, relationship="headOfHousehold", age=25):
    default = screen.household_members.create(
        relationship=relationship,
        age=age,
        student=False,
        student_full_time=False,
        pregnant=False,
        unemployed=False,
        worked_in_last_18_mos=True,
        visually_impaired=False,
        disabled=False,
        veteran=False,
        medicaid=False,
        disability_medicaid=False,
        has_income=True,
        has_expenses=True,
    )

    return default


# 1 parent 25 years old
# 2 children, 4 & 6 years old
# 1900 in monthly expenses between childcare and rent
# no assets
def create_single_parent_two_children_household(annual_income):
    white_label = WhiteLabel.objects.create(name="Test", code="test", state_code="CO")
    screen = Screen.objects.create(
        white_label=white_label,
        household_assets=0,
        household_size=3,
        zipcode="80204",
        agree_to_tos=True,
        housing_situation="renting",
        completed=False,
    )

    parent = create_default_household_member(screen)
    parent.expenses.create(type="rent", amount="1200", frequency="monthly", screen=screen)
    parent.expenses.create(type="childCare", amount="700", frequency="monthly", screen=screen)
    parent.income_streams.create(type="wages", amount=annual_income, frequency="yearly", screen=screen)

    create_default_household_member(screen, relationship="child", age=4)
    create_default_household_member(screen, relationship="child", age=6)

    return screen
