from configuration.white_labels.cesn import CesnConfigurationData
from screener.models import Screen

# The utility expenses the energy calculator asks about, as its config offers them.
ENERGY_EXPENSE_TYPES = list(CesnConfigurationData.energy_calculator_expense_options)


def has_renter_expenses(screen: Screen) -> bool:
    if screen.path != "renter":
        return True

    return screen.has_expense(ENERGY_EXPENSE_TYPES)
