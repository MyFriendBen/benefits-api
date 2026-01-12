from ..base import UrgentNeedFunction


class CentralFoodbank(UrgentNeedFunction):
    """
    Central Texas Foodbank

    Support with food banks, emergency food resources, and food related applications and services.

    counties :Bastrop, Bell, Blanco, Burnet, Caldwell, Coryell, Falls, Fayette, Freestone, Gillespie, Hays, Lampasas, Lee, Limestone, Llano, McLennan, Milam, Mills, San Saba, Travis and Williamson
    """

    dependencies = []

    def eligible(self) -> bool:
        # All users selecting food are eligible in the limited counties.
        # Specific counties managed via admin configuration
        return True
