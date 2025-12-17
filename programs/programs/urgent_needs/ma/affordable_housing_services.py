from ..base import UrgentNeedFunction


class AffordableHousingServices(UrgentNeedFunction):
    """
    Just a Start – Affordable Housing Services

    Program Details (from MA Benefits Sheet):
    - Name: Just A Start – Affordable Housing Services
    - Link: https://www.justastart.org
    - Application: https://www.justastart.org/housing/housing-assistance-programs/
    - Description: Helps residents access affordable rental and homeownership opportunities.

    Eligibility Rules:
    - Cambridge priority; housing-need based
    - Income Eligibility: Varies by housing program (AMI-based)
    - Resource Limits: Program-specific
    - Other Parameters: Cambridge residency often prioritized
    - Presumptive Eligibility: No
    - Citizenship Required: No (N/A)

    Application Process:
    - Time to Complete: 30–60 minutes
    - Time to Receive Benefit: 1 month
    - Required Docs: ID, income proof, housing application

    Value:
    - Benefit Type: Reduced expense (Below-market rent or purchase price)
    - Value Calculation: Program-specific
    """

    dependencies = []

    def eligible(self):
        """
        This program is available to all eligible households.

        Specific eligibility criteria (housing instability, Cambridge residency)
        are handled through:
        1. County filtering (Cambridge priority) - managed in admin
        2. UrgentNeedType association - shown when housing need is selected
        3. Resource limits and application requirements - managed in program details

        Returns True to allow the urgent need to be shown when:
        - User selects housing as an acute condition
        - User's county matches the program's eligible counties
        """
        return True
