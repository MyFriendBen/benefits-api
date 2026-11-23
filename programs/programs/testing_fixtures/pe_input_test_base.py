"""A shared household for tests that assert on the PolicyEngine payload.

`pe_input` builds the request from the screen and the calculators asked for, so nothing
here is tied to a state: a state's own input, such as its state code, comes from its
calculator, whichever white label the screen belongs to.
"""

from django.test import TestCase

from programs.programs.testing_fixtures.households import add_income, add_member, make_screen, make_white_label
from screener.models import Expense


class PeInputTestCase(TestCase):
    """Three members — a disabled head, a spouse and a student child.

    With `with_income`, the head has wages, self-employment and rental income, the spouse
    has a pension and Social Security retirement, and the household pays child support and
    medical expenses. Tests about the household's shape rather than its money turn it off.
    """

    with_income: bool = True

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.white_label = make_white_label()

    def setUp(self):
        super().setUp()

        self.screen = make_screen(
            household_size=3,
            zipcode="78701",
            county="Travis County",
            household_assets=5000,
        )
        self.head = add_member(self.screen, "headOfHousehold", 35, disabled=True)
        self.spouse = add_member(self.screen, "spouse", 32)
        self.child = add_member(self.screen, "child", 8, student=True)

        if not self.with_income:
            return

        for member, income_type, amount in (
            (self.head, "wages", 30000),
            (self.head, "selfEmployment", 5000),
            (self.head, "rental", 12000),
            (self.spouse, "pension", 8000),
            (self.spouse, "sSRetirement", 6000),
        ):
            add_income(member, amount, income_type=income_type, frequency="yearly")

        Expense.objects.create(screen=self.screen, type="childSupport", amount=500, frequency="monthly")
        Expense.objects.create(screen=self.screen, type="medical", amount=200, frequency="monthly")
