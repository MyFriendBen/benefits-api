from ..base import UrgentNeedFunction
from .example_urgent_need import ExampleUrgentNeed

# TODO: add this to /programs/programs/urgent_needs/__init__.py
{{code}}_urgent_need_functions: dict[str, type[UrgentNeedFunction]] = {
    "example_urgent_need": ExampleUrgentNeed,  # TODO: add state specific urgent needs
    # NOTE: For simple expense-based filtering, use required_expense_types field in Django admin
    # instead of creating a custom function
}
