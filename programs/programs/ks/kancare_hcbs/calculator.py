from programs.programs.calc import ProgramCalculator, Eligibility
from programs.programs import messages


class KsKancareHcbs(ProgramCalculator):
    """KanCare HCBS Waivers — flat $35,000/yr; single financial gate.

    Modeled as one program across Kansas's seven HCBS waivers. Eligibility:
      - Asset test: countable assets <= $2,000 for single applicants. Married
        applicants are NOT asset-gated (spousal-impoverishment protections the
        screener can't compute from a combined total; a warning message covers it).
      - SSI receipt bypasses the asset test.
      - Income, age, and disability flags do not gate (informational only).

    See spec.md for full eligibility rules, the data-gap inclusivity assumptions,
    and test scenarios.
    """

    asset_limit = 2_000
    amount = 35_000
    dependencies = [
        "household_assets",
    ]

    def _has_ssi(self) -> bool:
        """SSI confers automatic KanCare financial eligibility.

        Catches both the Screen `has_ssi` checkbox and any member SSI income
        stream, consistent with how other programs treat SSI categorical
        eligibility.
        """
        if self.screen.has_ssi:
            return True
        return any(
            member.calc_gross_income("yearly", ["sSI"]) > 0 for member in self.screen.household_members.all()
        )

    def household_eligible(self, e: Eligibility):
        # SSI recipients are automatically KanCare-financially-eligible and
        # bypass the asset test entirely.
        if self._has_ssi():
            e.condition(True, messages.presumed_eligibility())
            return

        # Married applicants are not asset-gated. Spousal-impoverishment rules
        # protect a large, applicant-dependent share of a couple's assets (the
        # Community Spouse Resource Allowance) that the screener cannot compute
        # from a single combined household-assets total. Applying the $2,000
        # single limit to a couple would wrongly exclude eligible married
        # households, so skip the asset test when a spouse/partner is present
        # (the config warning message surfaces this to married users).
        if self.screen.get_head().is_married()["is_married"]:
            e.condition(True)
            return

        # Single applicant: the only hard screener-testable gate is countable
        # assets at or below the individual asset limit (inclusive).
        assets = self.screen.household_assets if self.screen.household_assets is not None else 0
        e.condition(assets <= self.asset_limit, messages.assets(self.asset_limit))
