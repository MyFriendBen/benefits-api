import programs.programs.messages as messages
from programs.programs.calc import Eligibility, MemberEligibility, ProgramCalculator


class WaHeadStart(ProgramCalculator):
    """
    Head Start (WA) — federal program administered by local grantees.

    Combines Head Start Preschool (ages 3–5), Early Head Start (under 3 and pregnant women),
    and Migrant or Seasonal Head Start under a single entry per reviewer decision (2026-05-10).

    Eligibility requires:
      1. Age: under 3 OR pregnant (EHS path), or ages 3–5 (HS Preschool path)
      2. At least one financial pathway: household income ≤ 100% FPL, receipt of TANF/SSI/SNAP,
         or foster care for an age-eligible child (45 CFR § 1302.12(c)(1))

    Data gaps not evaluated by this calculator:
      - Homelessness (McKinney-Vento, § 1302.12(c)(1)(iii)): no reliable screener field
      - Migrant/seasonal agricultural worker pathway (§ 1302.12(f)): no screener field
      - Tribal program waiver (§ 1302.12(e)(1)): no field for tribal enrollment
      - Extended 100–130% FPL discretionary enrollment (§ 1302.12(d)): screener evaluates at 100%

    Benefit value: $10,381/year per eligible participant (WSIPP Program #272, 2023 dollars).
    Applied equally to EHS participants and pregnant women as a simplifying assumption.
    """

    # HS Preschool: ages 3–5 ("no older than required school age" = kindergarten-entry age in WA)
    hs_min_age = 3
    hs_max_age = 5
    # EHS: under age 3 or pregnant
    ehs_max_age = 3

    fpl_percent = 1.0  # 100% FPL per 45 CFR § 1302.12(c)(1)(i)
    member_amount = 10_381  # per eligible participant, annual (WSIPP Program #272)

    dependencies = [
        "age",
        "pregnant",
        "relationship",
        "household_size",
        "income_amount",
        "income_frequency",
    ]

    def member_eligible(self, e: MemberEligibility):
        member = e.member
        ehs_eligible = (member.age is not None and member.age < self.ehs_max_age) or member.pregnant
        hs_eligible = member.age is not None and self.hs_min_age <= member.age <= self.hs_max_age
        e.condition(ehs_eligible or hs_eligible)

    def household_eligible(self, e: Eligibility):
        e.condition(
            not self.screen.has_benefit("wa_head_start"),
            messages.must_not_have_benefit("Head Start"),
        )

        # Foster care categorical — any age-eligible member regardless of income (§ 1302.12(c)(1)(iv))
        has_foster_child = any(
            me.eligible and me.member.relationship == "fosterChild"
            for me in e.eligible_members
        )

        # TANF, SSI, SNAP categorical eligibility per OHS interpretation (ACF-IM-HS-22-03)
        categorical = (
            self.screen.has_benefit("tanf")
            or self.screen.has_benefit("ssi")
            or self.screen.has_benefit("snap")
        )

        gross_income = self.screen.calc_gross_income("yearly", ["all"])
        income_limit = int(self.fpl_percent * self.program.year.get_limit(self.screen.household_size))

        e.condition(
            categorical or has_foster_child or gross_income <= income_limit,
            messages.income(gross_income, income_limit),
        )
