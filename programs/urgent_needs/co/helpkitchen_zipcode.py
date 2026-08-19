from ..base import UrgentNeedFunction


class HelpkitchenZipcode(UrgentNeedFunction):
    dependencies = ["zipcode"]
    zipcodes = [
        "80010",
        "80011",
        "80012",
        "80013",
        "80014",
        "80015",
        "80016",
        "80017",
        "80018",
        "80019",
        "80045",
        "80102",
        "80112",
        "80137",
        "80138",
        "80230",
        "80231",
        "80238",
        "80247",
        "80249",
    ]

    def eligible(self):
        """
        Lives in a zipcode that is eligible for HelpKitchen
        """
        return self.screen.zipcode in self.zipcodes
