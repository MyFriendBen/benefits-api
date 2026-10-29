"""
Guard: a PolicyEngine input that sums expenses declares `expense_amount` and `expense_frequency`.

`calc_expenses` can't compute with a null amount or frequency, and payload assembly runs
before any calculator does, so an undeclared input read the row anyway and the crash cost
the screen every PolicyEngine program, reported to Sentry as an error. Declared, the row
gates only the programs that send the input, quietly, like any other unanswered field.
"""

import inspect

from django.test import SimpleTestCase

from programs.framework.pe_dependencies import household, member, spm, tax  # noqa: F401
from programs.framework.pe_dependencies.base import PolicyEngineScreenInput

EXPENSE_TOKENS = {"expense_amount", "expense_frequency"}


def _all_inputs(cls: type) -> list[type]:
    found = []
    for sub in cls.__subclasses__():
        found.append(sub)
        found.extend(_all_inputs(sub))
    return found


class TestExpenseReadingInputsDeclareTheirFields(SimpleTestCase):
    def test_every_input_that_sums_expenses_declares_amount_and_frequency(self) -> None:
        offenders = []
        for cls in _all_inputs(PolicyEngineScreenInput):
            value = cls.__dict__.get("value")
            if value is None or "calc_expenses" not in inspect.getsource(value):
                continue
            if not EXPENSE_TOKENS <= set(cls.dependencies):
                offenders.append(f"{cls.__module__}.{cls.__name__}")

        self.assertEqual(offenders, [], "declare expense_amount and expense_frequency on these")
