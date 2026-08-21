from screener.models import Screen


def has_renter_expenses(screen: Screen):
    if screen.path != "renter":
        return True

    return screen.has_expense(["heating", "cooling", "electricity"])
