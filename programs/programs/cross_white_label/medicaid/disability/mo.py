from dataclasses import dataclass, field
from decimal import Decimal

from screener.models import HouseholdMember
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages

# Streams whose reported amount may be wholly excluded by a rule MFB cannot observe, and so
# are removed in full by the inclusive second pass. `wages`/`selfEmployment` are the
# sheltered-workshop exclusion (which reaches any assistance-unit member, spouse included);
# `veteran` and `investment` each carry excluded sub-components MFB cannot isolate.
UNISOLABLE_TYPES = ("wages", "selfEmployment", "veteran", "investment")


@dataclass
class CountableIncome:
    """The countable-income computation, itemized.

    A test seam rather than a user- or API-facing output: several spec scenarios turn on a
    single stream's contribution or a single disregard's amount, because the rules they
    cover have no eligibility outcome to flip.

    All amounts are monthly, matching the thresholds Missouri publishes.
    """

    total: Decimal = Decimal(0)
    #: Per-stream contribution to the count, keyed by income type, after stream-level
    #: exclusions (SSI, cash assistance) and disregards (spouse earned, first-$50 SSDI).
    contributions: dict[str, Decimal] = field(default_factory=dict)
    #: Each case-level disregard's applied amount, keyed by name.
    disregards: dict[str, Decimal] = field(default_factory=dict)

    def contribution(self, income_type: str) -> Decimal:
        return self.contributions.get(income_type, Decimal(0))


class MoTwha(ProgramCalculator):
    """
    Ticket to Work Health Assurance (MO) — MO HealthNet buy-in for workers with disabilities.

    TWHA lets employed Missourians with disabilities keep or obtain MO HealthNet coverage at
    income levels above regular MO HealthNet. Eligibility (RSMo 208.146, effective
    2026-08-28; DSS manual 0855.000.00):

      1. Age 16 through 64, inclusive of the calendar month the person turns 16 or 65
      2. Qualifying disability — screened via ``long_term_disability`` /
         ``visually_impaired`` (NOT the generic ``disabled`` flag, matching the
         KS Working Healthy and awd_medicaid precedent)
      3. Employed with earned income (wages / self-employment), no dollar floor
      4. Countable resources at or below $6,220 (single) / $12,441 (couple) — but reported
         assets never produce a denial; see the asset note below
      5. Countable income at or below 250% FPL, except that the worker's own earned income
         between the 250% and 300% boundaries is excluded from the count
      6. Missouri resident — handled by white-label routing
      7. Citizen or qualified non-citizen — handled by config ``legal_status_required``

    The assistance unit is the single individual or the married couple, never MFB's generic
    household size: dependent children neither enlarge the unit nor raise the income or
    asset thresholds, and each spouse is evaluated independently as "the worker" with the
    other treated as "the spouse."

    Two rules deliberately never deny:

    - **Assets.** ``household_assets`` is a single aggregate that both overstates countable
      resources (TWHA excludes retirement accounts entirely, and medical savings and
      independent living accounts up to $5,000/year each) and understates them (Missouri's
      permanent-and-total-disability framework counts property MFB has no field for). So an
      over-limit figure is not a denial ground; the limit is selected for the assistance
      unit and applied only in the passing direction.
    - **Unisolable income.** TWHA incorporates MHABD's exclusion list, which removes
      sheltered-workshop earnings from the income test entirely and removes specific
      veteran-benefit and ABLE-account sub-components MFB cannot isolate. Rather than
      guess a portion, ``_countable_income`` runs twice: an ordinary pass, then — only if
      the ordinary pass would deny — an inclusive pass with every unisolable stream removed
      in full, compared against the 250% boundary. Because that pass removes all earned
      income, a household whose excess is entirely earned income is always eligible, at any
      income level; MFB's practical earned-income ceiling is therefore unbounded and the
      program description must not present an income ceiling as a screening outcome.

    Employer-sponsored insurance is post-eligibility coordination of benefits (HIPP), not an
    eligibility criterion — ``Insurance.employer`` appears in no gate here, deliberately.

    Data gaps, all resolved inclusively (see specs/mo.md): the formal PTD/MRT disability
    determination, whether earned income meets TWHA's Medicare/Social Security tax rule,
    the Medically Improved Group's 40-hour employment floor, resource composition,
    residency intent, and the split between health-insurance premiums, dental/optical
    premiums, and medical bills within the generic ``medical`` expense.
    """

    program_code = "mo_twha"

    min_age = 16
    max_age = 64

    # Appendix J's own cent boundaries, monthly, effective 2026-04-01. Used directly rather
    # than derived from FPL: Missouri publishes these as the operative comparison values.
    income_boundary_250 = {1: Decimal("3324.99"), 2: Decimal("4508.99")}
    income_ceiling_300 = {1: Decimal("3990.00"), 2: Decimal("5410.00")}

    # Effective 2026-07-01. The screener accepts whole dollars, so the cent-level statutory
    # limits ($6,220.50 / $12,441.00) are expressed as the boundary values a screen can state.
    resource_limits = {1: 6_220, 2: 12_441}

    # Monthly statutory disregards (criterion 5's ordered list).
    spouse_earned_disregard = Decimal(50_000) / 12  # first $50,000/year of a spouse's earned income
    standard_deduction = Decimal(20)  # once per case
    dental_optical_deduction = Decimal(75)  # or actual, if higher; MFB always applies the floor
    ssdi_disregard = Decimal(50)  # first $50/month of the worker's SSDI
    earned_percent = Decimal("0.5")  # half of the worker's own earned income

    # $12,200/yr per eligible member: Missouri's average Medicaid benefit spending per
    # full-year-equivalent enrollee, all enrollees, FY2024 — $15,891,669,916 / 1,302,603 FYE
    # enrollees (MACPAC Exhibit 23, February 2026). A statewide proxy is used rather than the
    # TWHA-specific mean of $46,819, which is concentrated in ID/DD waiver spending (71% of
    # December 2025 TWHA payments) and so misrepresents a typical member. An estimated value
    # of coverage, not a cash payment. See specs/mo.md Benefit Value.
    member_amount = 12_200

    dependencies = [
        "age",
        "household_size",
        "income_type",
        "income_amount",
        "income_frequency",
        "household_assets",
        "relationship",
        "expenses",
    ]

    def household_eligible(self, e: Eligibility):
        # Reported assets are only ever applied in the passing direction (see class note), so
        # this reports the limit without being able to fail the household on it.
        e.condition(True, messages.assets(self.resource_limits[self._assistance_unit_size(self.screen.get_head())]))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        # Age 16 through 64, inclusive of the calendar month the person turns 16 or 65.
        e.condition(self._age_eligible(member))

        # Qualifying disability. The generic `disabled` flag is deliberately not read: it
        # admits short-term conditions the statutory standard excludes.
        e.condition(bool(member.long_term_disability) or bool(member.visually_impaired))

        # Employed, with no floor beyond having some earned income. Read through the `earned`
        # selector, which covers both wages and self-employment — reading `wages` alone would
        # deny every self-employed applicant.
        e.condition(member.calc_gross_income("monthly", ["earned"]) > 0)

        # Countable income, evaluated against this member as "the worker."
        e.condition(self._income_eligible(member))

    def member_value(self, member: HouseholdMember) -> int:
        return self.member_amount

    def _age_eligible(self, member: HouseholdMember) -> bool:
        """Whether this member is age 16 through 64, counting the birthday month itself at
        both ends (0855.005.05: "includes the month the person turns age 16 or 65").

        ``calc_age`` already treats the birth month as attained — it compares
        ``reference.month >= birth.month`` — so it reads 16 from the first day of the
        16th-birthday month, which is the floor TWHA wants. The ceiling needs one more month
        than ``age <= 64`` allows: someone in their 65th-birthday month reads as 65 and is
        still covered, while the month after is not. So 65 passes only when the reference
        date is inside the birthday month itself.

        A member with neither a stored birth date nor an age fails closed.
        """
        try:
            age = member.calc_age()
        except (TypeError, AttributeError):
            return False

        if age is None:
            return False

        if self.min_age <= age <= self.max_age:
            return True

        # The 65th-birthday month. Decidable only from a stored birth month; a bare `age`
        # integer cannot distinguish it from one month later, so it fails closed.
        if age == self.max_age + 1 and member.birth_month is not None:
            return member.birth_month == self.screen.get_reference_date().month

        return False

    def _assistance_unit(self, worker: HouseholdMember) -> list[HouseholdMember]:
        """The worker, plus their spouse if there is one. Never the whole household —
        dependent children are outside the TWHA assistance unit entirely."""
        marriage = worker.is_married()
        spouse = marriage.get("married_to") if marriage.get("is_married") else None

        # A spouse relationship that cannot be resolved to a member (the head's spouse is
        # found by scanning, so this is defensive) leaves a single-person unit.
        if spouse is None or spouse.id == worker.id:
            return [worker]

        return [worker, spouse]

    def _assistance_unit_size(self, worker) -> int:
        if worker is None:
            return 1

        return len(self._assistance_unit(worker))

    def _income_eligible(self, worker: HouseholdMember) -> bool:
        """Whether countable income admits this worker, per criterion 5 and Data Gap 7.

        Ordinary pass first. Where it would deny, the inclusive pass recomputes with every
        unisolable stream removed in full and is compared against the 250% boundary — the
        300% band ceiling cannot apply there, since that pass leaves no earned income for the
        band allowance (which covers only worker-earned excess) to cover.
        """
        size = self._assistance_unit_size(worker)
        boundary = self.income_boundary_250[size]

        ordinary = self._countable_income(worker)
        if ordinary.total <= boundary:
            return True

        # The 250-300% band: eligible only if the entire excess above the 250% boundary is the
        # worker's own earned income, after the half-earned deduction. Excess from any other
        # source — a spouse's income, or the worker's own unearned income — is not excluded.
        if ordinary.total <= self.income_ceiling_300[size]:
            worker_earned = sum(
                (ordinary.contribution(t) for t in ("wages", "selfEmployment")),
                Decimal(0),
            )
            if ordinary.total - worker_earned <= boundary:
                return True

        inclusive = self._countable_income(worker, exclude_unisolable=True)

        return inclusive.total <= boundary

    def _countable_income(self, worker: HouseholdMember, exclude_unisolable: bool = False) -> CountableIncome:
        """Monthly countable income for ``worker``, applying criterion 5's disregards in order.

        Derived from the itemized disregards rather than by comparing gross income to
        Appendix J's $3,990/$5,410 figures — those are DSS's pre-computed ceiling for the
        all-earned-income case, so comparing against them directly would misclassify any
        household with a spouse, SSI, SSDI, or a mix of earned and unearned income.

        ``exclude_unisolable`` runs Data Gap 7's inclusive pass: every stream that may be
        wholly excluded by a rule MFB cannot observe is removed in full. The half-earned
        deduction still applies to the worker's own earned income even when that income is
        itself excluded — the two treatments are independent.
        """
        result = CountableIncome()
        unit = self._assistance_unit(worker)
        spouse_disregard_remaining = self.spouse_earned_disregard

        for member in unit:
            is_worker = member.id == worker.id

            for stream in member.income_streams.all():
                amount = Decimal(str(stream.monthly()))
                income_type = stream.type

                # Temporary Assistance cash grants are excluded entirely.
                if income_type == "cashAssistance":
                    self._record(result, income_type, Decimal(0))
                    continue

                # SSI is excluded in full.
                if income_type == "sSI":
                    self._record(result, income_type, Decimal(0))
                    continue

                if exclude_unisolable and income_type in UNISOLABLE_TYPES:
                    self._record(result, income_type, Decimal(0))
                    continue

                if is_worker:
                    # First $50/month of the worker's own SSDI.
                    if income_type == "sSDisability":
                        amount = max(Decimal(0), amount - self.ssdi_disregard)
                        result.disregards["ssdi"] = self.ssdi_disregard
                elif income_type in ("wages", "selfEmployment"):
                    # First $50,000/year of the spouse's earned income, applied across the
                    # spouse's earned streams. Not conditioned on the spouse's own disability
                    # status: neither the statute nor the operative manual so limits it, and
                    # a dual-TWHA couple is a case the manual plainly contemplates.
                    applied = min(amount, spouse_disregard_remaining)
                    spouse_disregard_remaining -= applied
                    amount -= applied
                    result.disregards["spouse_earned"] = result.disregards.get("spouse_earned", Decimal(0)) + applied

                self._record(result, income_type, amount)

        # Half of the worker's own earned income, as reported — applied whether or not that
        # income was itself excluded above.
        worker_gross_earned = Decimal(str(worker.calc_gross_income("monthly", ["earned"])))
        half_earned = worker_gross_earned * self.earned_percent
        result.disregards["half_earned"] = half_earned

        # Case-level deductions, applied once.
        result.disregards["standard"] = self.standard_deduction
        result.disregards["dental_optical"] = self.dental_optical_deduction

        # The full reported `medical` expense is treated as the health-insurance premium: the
        # screener collects one generic category and cannot isolate a premium from a bill.
        medical = Decimal(str(self.screen.calc_expenses("monthly", ["medical"])))
        result.disregards["health_insurance_premium"] = medical

        counted = sum(result.contributions.values(), Decimal(0))
        result.total = max(
            Decimal(0),
            counted - half_earned - self.standard_deduction - self.dental_optical_deduction - medical,
        )

        return result

    @staticmethod
    def _record(result: CountableIncome, income_type: str, amount: Decimal) -> None:
        result.contributions[income_type] = result.contributions.get(income_type, Decimal(0)) + amount
