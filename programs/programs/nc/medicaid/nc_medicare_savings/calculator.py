from programs.framework.base import MemberEligibility
from programs.programs.federal.medicare_savings.calculator import MedicareSavings
from typing import ClassVar


class MedicareSavingsNC(MedicareSavings):
    program_code = "nc_medicare_savings"
    ineligible_insurance_types: ClassVar[tuple[str, ...]] = ("va", "medicaid")
    asset_limit: ClassVar[dict[str, int]] = {"single": 9_660, "married": 14_470}
    medicaid_asset_limit: ClassVar[dict[str, int]] = {"single": 2_000, "married": 3_000}  # NC ABD Medicaid
    # NC-specific: 2026 Medicare Part B premium ($202.90/month → rounded to $203/month per eligible member)
    # Source: https://www.cms.gov/newsroom/fact-sheets/2026-medicare-parts-b-premiums-deductibles
    member_amount: ClassVar[int] = 203 * 12
    # Living Allowance for SSI deeming (MA-2260 §IV.D-E). Update annually.
    living_allowance: ClassVar[int] = 498 * 12
    # Monthly income increment per person beyond family size 8 at 135% FPL. Update annually.
    additional_per_person: ClassVar[int] = 639 * 12

    def member_eligible(self, e: MemberEligibility):
        """
        They qualify if any of these are true:
            Reports Medicare as their health insurance
            Age > 65 (regardless of insurance)
            Reports SSDI income (regardless of age)
        Automatic disqualifiers:
            Reports SSI income (they get full Medicaid instead)
        """
        member = e.member
        _, spouse = self.get_marital_status(member)

        # Medicare eligibility: any one of these qualifies
        e.condition(
            member.age >= self.min_age
            or member.has_insurance_types(("medicare",), strict=False)
            or member.calc_gross_income("yearly", ["sSDisability"]) > 0
        )

        # Asset limit
        status = "married" if spouse else "single"
        e.condition(self.screen.household_assets <= self.asset_limit[status])

        # NC-specific disqualifiers
        e.condition(not self.screen.has_benefit("nc_aca"))
        e.condition(not member.insurance.has_insurance_types(self.ineligible_insurance_types))
        e.condition(member.calc_gross_income("yearly", ["sSI"]) == 0)

        self.check_income_limits(e, member, spouse)

    def check_income_limits(self, e: MemberEligibility, member, spouse):
        """
        NC MQB-Q two-step income evaluation:
        Step 1: SSI budgeting - individual or couple only, income <= 100% FPL, spouse income deemed.
        Step 2: Court-ordered family size - applicant + spouse + dependents under 18, no deeming.
        Eligible if either step passes.
        """

        e.condition(self._passes_ssi_budgeting(member, spouse) or self._passes_family_size_methodology(member, spouse))

    def _passes_ssi_budgeting(self, member, spouse) -> bool:
        """Step 1: individual/couple SSI budgeting, income <= 100% FPL."""

        """
        1a. Classify the a/b into one of four categories:

        Category	        Condition	                            Income counted

        Medicaid            Unmarried 18+, or spouse/parent         a/b's income only
        Individual          already on SSI
                        	
        Medicaid            Married, living together, both          Combined spousal income
        Couple              MQB-eligible, neither on SSI

        Individual w/       Married, spouse not on                  a/b's income + deemed spouse income
        Ineligible          Medicare/Medicaid/SSI	
        Spouse	
        
        Medicaid            Under 18, living with parent(s)         a/b's income + deemed parent income
        Child	            not on SSI

        """

        classification = self._classify_applicant(member, spouse)

        if classification == "medicaid_individual":
            earned, unearned, _ = self.get_combined_income(member, spouse=None, include_ssi=False)
            earned, unearned = self.apply_income_disregards(earned, unearned)
            countable_income = earned + unearned
            household_size = 1

        elif classification == "medicaid_couple":
            earned, unearned, _ = self.get_combined_income(member, spouse, include_ssi=False)
            earned, unearned = self.apply_income_disregards(earned, unearned)
            countable_income = earned + unearned
            household_size = 2

        elif classification == "individual_with_ineligible_spouse":
            # Apply disregards to a/b's own income first, then add deemed spouse income separately
            earned, unearned, _ = self.get_combined_income(member, spouse=None, include_ssi=False)
            earned, unearned = self.apply_income_disregards(earned, unearned)
            countable_income = earned + unearned + self._calc_deemed_income(spouse)
            household_size = 1

        else:  # medicaid_child
            # Apply disregards to a/b's own income first, then add deemed parent income separately
            earned, unearned, _ = self.get_combined_income(member, spouse=None, include_ssi=False)
            earned, unearned = self.apply_income_disregards(earned, unearned)
            deemed_total = sum(self._calc_deemed_income(p) for p in self._get_parents_in_household(member))
            countable_income = earned + unearned + deemed_total
            household_size = 1

        fpl = self.program.year.as_dict().get(household_size)
        if fpl is None:
            return False

        if countable_income > fpl:
            return False
        # Income <= 100% FPL: only qualify for MSP if assets disqualify from full Medicaid
        status = "married" if spouse else "single"
        return self.screen.household_assets > self.medicaid_asset_limit[status]

    def _classify_applicant(self, member, spouse) -> str:
        """
        Classify a/b per SSI budgeting methodology (MA-2260, Section III.1a).
        Returns one of: medicaid_individual, medicaid_couple,
                        individual_with_ineligible_spouse, medicaid_child.
        """
        if member.age < 18:
            parents_on_ssi = any(
                p.calc_gross_income("yearly", ["sSI"]) > 0
                for p in self._get_parents_in_household(member, exclude_ssi=False)
            )
            return "medicaid_individual" if parents_on_ssi else "medicaid_child"
        if not spouse:
            return "medicaid_individual"
        if spouse.calc_gross_income("yearly", ["sSI"]) > 0:
            return "medicaid_individual"  # spouse already on SSI
        spouse_medicare_eligible = (
            spouse.has_insurance_types(("medicare",), strict=False)
            or spouse.age >= self.min_age
            or spouse.calc_gross_income("yearly", ["sSDisability"]) > 0
        )
        if spouse_medicare_eligible:
            return "medicaid_couple"
        return "individual_with_ineligible_spouse"

    def _calc_deemed_income(self, other_member) -> float:
        """
        Deemed income from ineligible spouse/parent after Living Allowance deduction
        (MA-2260, §IV.D-E). Allowance applied to unearned income first, then earned.
        """
        earned = other_member.calc_gross_income("yearly", ["earned"])
        unearned = other_member.calc_gross_income("yearly", ["unearned"], ["sSI"])

        if unearned >= self.living_allowance:
            unearned -= self.living_allowance
        else:
            remaining = self.living_allowance - unearned
            unearned = 0
            earned = max(0, earned - remaining)

        return max(0, earned + unearned)

    def _get_parents_in_household(self, member, exclude_ssi: bool = True) -> list:
        """Return parent(s) of the member. Excludes SSI recipients when exclude_ssi is True."""
        household = list(self.screen.household_members.all())
        parent_relationships = (
            ("headOfHousehold", "spouse", "domesticPartner")
            if member.relationship in ("child", "fosterChild")
            else ("parent", "fosterParent")
        )
        return [
            m
            for m in household
            if m.relationship in parent_relationships
            and (not exclude_ssi or m.calc_gross_income("yearly", ["sSI"]) == 0)
        ]

    def _passes_family_size_methodology(self, member, spouse) -> bool:
        """Step 2: court-ordered family size, no spousal income deeming."""
        household = list(self.screen.household_members.all())

        dependents = [
            m for m in household if m.pk != member.pk and (spouse is None or m.pk != spouse.pk) and m.age < 18
        ]
        # Skip step 2 entirely if no dependents under 18 in the home
        if not dependents:
            return False

        family_size = 1 + (1 if spouse else 0) + len(dependents)

        # Same income sources as step 1 but without deeming - children's own income excluded
        classification = self._classify_applicant(member, spouse)
        if classification == "medicaid_child":
            income_sources = [member] + self._get_parents_in_household(member)
        else:
            income_sources = [member] + ([spouse] if spouse else [])

        earned_total, unearned_total = 0, 0
        for m in income_sources:
            earned, unearned, _ = self.get_combined_income(m, spouse=None, include_ssi=False)
            earned_total += earned
            unearned_total += unearned

        earned_total, unearned_total = self.apply_income_disregards(earned_total, unearned_total)
        countable_income = earned_total + unearned_total

        max_income = self._get_family_size_income_limit(family_size)
        if max_income is None:
            return False

        return countable_income <= max_income

    def _get_family_size_income_limit(self, family_size: int) -> float | None:
        """Chart-based income limit for step 2. For family size > 8, add $639/month per additional person."""
        capped_size = min(family_size, 8)
        _, max_income = self.get_fpl_limits(capped_size)
        if max_income is None:
            return None
        if family_size > 8:
            max_income += self.additional_per_person * (family_size - 8)

        return max_income
