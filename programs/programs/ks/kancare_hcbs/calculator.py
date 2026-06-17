from programs.programs.calc import ProgramCalculator, Eligibility
from programs.programs import messages


class KsKancareHcbs(ProgramCalculator):
    """KanCare HCBS (Home and Community-Based Services) Waivers.

    Kansas operates seven HCBS waivers through KanCare (Kansas Medicaid) that
    provide in-home/community services to people who would otherwise require
    institutional care (Frail Elderly, Physical Disability, I/DD, Autism,
    Brain Injury, Serious Emotional Disturbance, Technology Assisted).

    Per the spec, this is modeled as a single program rather than split per
    waiver. The only hard screener-testable gate is the financial asset test;
    the formal KDADS assessment process gates functional eligibility downstream.

    Eligibility (per spec):
      - Asset limit: countable assets <= $2,000 for a single applicant. Married
        applicants are NOT asset-gated: spousal-impoverishment rules protect a
        large, applicant-dependent share (the Community Spouse Resource
        Allowance, up to ~$162,660 in 2026) that the screener cannot compute
        because it captures only a combined household-asset total with no
        per-spouse split. Applying the single $2,000 limit to a couple would
        wrongly exclude eligible married households, so the asset test is not
        applied when a spouse/partner is present (inclusivity assumption — the
        config warning message tells married users their assets were not
        considered and KanCare verifies at application).
      - SSI auto-eligibility: SSI recipients (the `has_ssi` checkbox or any SSI
        income stream) are automatically KanCare-financially-eligible and bypass
        the asset test.
      - Income does NOT disqualify: income above the $2,982/month (300% SSI FBR,
        2026) cost-share threshold triggers a patient-liability/Miller-Trust
        obligation but does not gate screener eligibility.
      - Age does NOT filter: Brain Injury (0-64) plus Frail Elderly (65+) cover
        every age, so at least one waiver applies regardless of age.
      - Disability flags do NOT gate: informational only; functional/diagnostic
        eligibility is a downstream assessment.

    Data gaps (handled with inclusivity assumptions per spec): nursing-facility
    level of care, specific disability type / SSA determination, community-living
    intent, citizenship/immigration status, AU 3-year limit, 5-year asset
    transfer look-back, and the spousal asset split (married applicants are not
    asset-gated; see above). The waitlist caveat is surfaced via the config
    warning message and program description.
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
