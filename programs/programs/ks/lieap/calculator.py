from programs.programs.calc import ProgramCalculator, Eligibility
import programs.programs.messages as messages
from typing import ClassVar


class KsLieap(ProgramCalculator):
    """KS LIEAP (Low Income Energy Assistance Program) — heating/cooling bill
    assistance administered by Kansas DCF.

    Eligibility (see spec.md):
      * Criterion 1: household gross income at or below 150% FPL, unless
        categorically eligible.
      * Criterion 2: categorical eligibility — a household member receiving SNAP,
        TANF, or SSI qualifies regardless of income.
      * Criterion 4: the household must be responsible for home energy costs
        (directly or as part of rent). The spec maps this to home-owner / renter /
        utility-provider fields, but those live only on the CO-specific
        `energy_calculator` sub-model and are never populated in the standard KS
        screener. Following the nc_lieap precedent (the state program named in the
        ticket), responsibility is inferred from a rent / mortgage / heating
        expense — a household with none (e.g. energy paid entirely by a landlord
        with no pass-through) is excluded.

    Handled outside the calculator:
      * Criterion 3 (KS residency) — enforced by white-label routing / the
        location picker.
      * Criterion 5 (citizenship) — enforced by the program's
        `legal_status_required` config, not screened as a question.
      * "Already receiving LIEAP this season" — surfaced via the `has_ks_lieap`
        current-benefit field and the framework's `already_has` flag, not
        calculator logic.

    Data gaps (Criteria 6 & 7 — institutionalization and subsidized housing with
    heating included in rent) are not built as hard exclusions per the inclusive
    principle; they are surfaced as notes.

    Benefit value is a flat $680/year — DCF's reported statewide average benefit,
    used because the fuel-provider rate-tier matrix that sets the real amount is
    not published.
    """

    fpl_percent = 1.5
    amount = 680
    expenses = ("rent", "mortgage", "heating")
    dependencies: ClassVar[list[str]] = [
        "income_frequency",
        "income_amount",
        "household_size",
    ]

    def household_eligible(self, e: Eligibility):
        # Criterion 4: responsible for home energy costs (directly or via rent)
        e.condition(self.screen.has_expense(self.expenses))

        # Criteria 1 & 2: income at or below 150% FPL, unless categorically
        # eligible via SNAP / TANF / SSI (which bypasses the income test only).
        if self._categorically_eligible():
            e.condition(True, messages.presumed_eligibility())
        else:
            gross_income = int(self.screen.calc_gross_income("yearly", ["all"]))
            income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))
            e.condition(gross_income <= income_limit, messages.income(gross_income, income_limit))

    def _categorically_eligible(self) -> bool:
        """A household member receiving SNAP, TANF, or SSI qualifies regardless of
        income (Criterion 2). SNAP/TANF/SSI receipt is read via `has_base_benefit`
        so KS variants (`ks_snap`, `ks_ssi`, ...) are matched. SSI additionally
        counts an sSI income stream (`has_ssi_or_ssi_income`), since a KS SSI
        income stream is not auto-written to the current-benefit table."""
        return (
            self.screen.has_base_benefit("snap")
            or self.screen.has_base_benefit("tanf")
            or self.screen.has_base_benefit("ssi")
            or self.screen.calc_gross_income("yearly", ["sSI"]) > 0
        )
