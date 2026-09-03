from dataclasses import dataclass, field
from decimal import Decimal

from screener.models import HouseholdMember
from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages

# Streams the second pass removes in full, because whether an exclusion applies to them
# depends on a fact the screener does not collect. Rationale per type: specs/mo.md Data Gap 7.
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

    Eligibility, benefit value, sources and data gaps are specified in ``specs/mo.md``; this
    docstring covers only what the shape of the code needs explaining.

    Two structural choices that are not obvious from reading the methods:

    - **The assistance unit is the individual or married couple, not the household.** Every
      income and resource threshold is sized to that unit, so ``household_size`` is never
      the index — see ``_assistance_unit``. Each spouse is evaluated in turn as "the
      worker," the other as "the spouse."
    - **An ineligible income result is only returned after a second pass.** Some exclusions
      turn on facts the screener cannot see, so ``_countable_income`` is computed twice; see
      ``_income_eligible``. One consequence is worth knowing before reading the thresholds
      as limits: because the second pass drops earned income entirely, excess that is purely
      earned never denies at any amount.

    Reported assets and unreported exclusions only ever widen eligibility here — neither
    produces a denial. Coverage type is not consulted at all, so employer-sponsored
    insurance cannot disqualify.
    """

    program_code = "mo_twha"

    min_age = 16
    max_age = 64

    # Missouri publishes these as the operative monthly comparison values, so they are used
    # directly rather than derived from FPL. Keyed by assistance-unit size.
    income_boundary_250 = {1: Decimal("3324.99"), 2: Decimal("4508.99")}
    income_ceiling_300 = {1: Decimal("3990.00"), 2: Decimal("5410.00")}

    # The screener accepts whole dollars, so these are the boundary values a screen can
    # actually state rather than the statutory cent-level limits.
    resource_limits = {1: 6_220, 2: 12_441}

    # Monthly amounts for the disregards applied in `_countable_income`.
    spouse_earned_disregard = Decimal(50_000) / 12
    standard_deduction = Decimal(20)
    dental_optical_deduction = Decimal(75)
    ssdi_disregard = Decimal(50)
    earned_percent = Decimal("0.5")

    # Annual per-member estimated value of coverage, not a cash payment.
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
        # Passes unconditionally: this surfaces the limit as a message without letting a
        # reported figure deny. See specs/mo.md criterion 4.
        e.condition(True, messages.assets(self.resource_limits[self._assistance_unit_size(self.screen.get_head())]))

    def member_eligible(self, e: MemberEligibility):
        member = e.member

        e.condition(self._age_eligible(member))

        # `disabled` is deliberately not read — it is broader than the standard this
        # screens for. See specs/mo.md criterion 2.
        e.condition(bool(member.long_term_disability) or bool(member.visually_impaired))

        # `earned` rather than `wages`: the selector also covers self-employment, which
        # qualifies. No floor beyond a nonzero amount.
        e.condition(member.calc_gross_income("monthly", ["earned"]) > 0)

        # Evaluated with this member as "the worker."
        e.condition(self._income_eligible(member))

    def member_value(self, member: HouseholdMember) -> int:
        return self.member_amount

    def _age_eligible(self, member: HouseholdMember) -> bool:
        """Whether this member is within the age range, birthday month inclusive at both ends.

        ``calc_age`` already counts the birth month as attained (it compares
        ``reference.month >= birth.month``), which gives the inclusive floor for free. The
        ceiling needs one month more than ``max_age`` allows, hence the second branch —
        without it, coverage would end a month early.
        """
        age = member.calc_age()
        if age is None:
            return False

        if self.min_age <= age <= self.max_age:
            return True

        # The birthday month itself. Only decidable from a stored birth month — a bare `age`
        # integer cannot tell it from a month later — so that case fails closed.
        if age == self.max_age + 1 and member.birth_month is not None:
            return member.birth_month == self.screen.get_reference_date().month

        return False

    def _assistance_unit(self, worker: HouseholdMember) -> list[HouseholdMember]:
        """The worker, plus their spouse if there is one — never the whole household."""
        marriage = worker.is_married()
        spouse = marriage.get("married_to") if marriage.get("is_married") else None

        # `is_married` resolves the head's spouse by scanning, so guard the unresolved case.
        if spouse is None or spouse.id == worker.id:
            return [worker]

        return [worker, spouse]

    def _assistance_unit_size(self, worker: HouseholdMember) -> int:
        return len(self._assistance_unit(worker))

    def _income_eligible(self, worker: HouseholdMember) -> bool:
        """Whether countable income admits this worker. See specs/mo.md criterion 5 + Data Gap 7.

        Ordinary pass first; only where that would deny does the second pass run. The second
        pass compares against the 250% boundary rather than the 300% ceiling because it
        leaves no earned income for the band allowance to apply to.
        """
        size = self._assistance_unit_size(worker)
        boundary = self.income_boundary_250[size]

        ordinary = self._countable_income(worker)
        if ordinary.total <= boundary:
            return True

        # The band allowance covers only the worker's own earned excess, so subtract that
        # and require what remains to clear the boundary on its own.
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
        """Monthly countable income for ``worker``. Disregards and their order: specs/mo.md
        criterion 5.

        Built up from the itemized disregards, which is what makes the result comparable to
        the published thresholds; the order below is load-bearing.

        ``exclude_unisolable`` runs the second pass, removing ``UNISOLABLE_TYPES`` in full.
        Note the half-earned deduction still applies to the worker's earned income even when
        that income was itself removed — the two are independent.
        """
        result = CountableIncome()
        unit = self._assistance_unit(worker)
        spouse_disregard_remaining = self.spouse_earned_disregard

        for member in unit:
            is_worker = member.id == worker.id

            for stream in member.income_streams.all():
                amount = Decimal(str(stream.monthly()))
                income_type = stream.type

                if income_type == "cashAssistance":
                    self._record(result, income_type, Decimal(0))
                    continue

                if income_type == "sSI":
                    self._record(result, income_type, Decimal(0))
                    continue

                if exclude_unisolable and income_type in UNISOLABLE_TYPES:
                    self._record(result, income_type, Decimal(0))
                    continue

                if is_worker:
                    if income_type == "sSDisability":
                        amount = max(Decimal(0), amount - self.ssdi_disregard)
                        result.disregards["ssdi"] = self.ssdi_disregard
                elif income_type in ("wages", "selfEmployment"):
                    # Spread across the spouse's earned streams, and deliberately not
                    # conditioned on the spouse's own disability status.
                    applied = min(amount, spouse_disregard_remaining)
                    spouse_disregard_remaining -= applied
                    amount -= applied
                    result.disregards["spouse_earned"] = result.disregards.get("spouse_earned", Decimal(0)) + applied

                self._record(result, income_type, amount)

        # Computed from reported earned income, so it survives the second pass removing it.
        worker_gross_earned = Decimal(str(worker.calc_gross_income("monthly", ["earned"])))
        half_earned = worker_gross_earned * self.earned_percent
        result.disregards["half_earned"] = half_earned

        # Case-level deductions, applied once.
        result.disregards["standard"] = self.standard_deduction
        result.disregards["dental_optical"] = self.dental_optical_deduction

        # The screener has one generic `medical` category, so the whole reported amount is
        # taken as the premium. See specs/mo.md Data Gap 6.
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
