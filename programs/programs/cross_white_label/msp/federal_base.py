"""Medicare Savings Programs — MFB federal base."""

from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from math import ceil
from typing import ClassVar, Literal, Optional

from programs.framework.base import MemberEligibility, ProgramCalculator
from screener.models import HouseholdMember

Route = Literal["qmb", "slmb", "qi", "qdwi"]
FamilySizeMethod = Literal["individual_or_couple", "extra_help"]

# Two members who give the same one of these relationships to the head are read as a
# married couple: the head's parents, step-parents, foster parents or grandparents.
PARENT_TYPE_RELATIONSHIPS = frozenset({"parent", "stepParent", "fosterParent", "grandParent"})


def _exact(amount: float) -> Decimal:
    """A screener income figure as an exact decimal.

    `calc_gross_income` sums in float, so a total that is a whole dollar can arrive a
    fraction of a cent off. The income limits are whole dollars and SLMB's and QI's tops
    are strict, so that drift can move a household across a line. Rounding to a millionth
    removes it and leaves every real amount, including a yearly figure divided by 12, intact.
    """
    return Decimal(str(round(amount, 6)))


class MspFederalBase(ProgramCalculator, abstract=True):
    """
    The four federal Medicare Savings Program groups, computed in our own code:

    - QMB: Medicare, countable income at or below 100% of the poverty line. Pays the Part B
      premium (plus Part A premium and cost sharing, not counted).
    - SLMB: Medicare, countable income above QMB's limit and below 120%. Pays Part B.
    - QI: Medicare, countable income from 120% to below 135%, and no Medicaid. Pays Part B.
    - QDWI: disabled workers under 65 who lost premium-free Part A through earnings. Held:
      the screener can't see the defining condition, so it is not evaluated unless a state
      sets ``evaluate_qdwi``.

    Each member is judged alone, with their spouse's income and the couple limits. Countable
    income is monthly, by SSI rules: the $20 general disregard (unearned first, then
    earned, never against SSI or cash assistance), then $65 and half of the remaining
    earnings. Investment income is left out. Each limit is the percentage of the monthly
    poverty line rounded up to the dollar, as CMS computes it (SSA POMS HI 00815.023),
    computed exactly so a boundary household doesn't drift across a strict top.

    Savings use the one household figure against the individual or couple limit.

    A spouse is the head's ``spouse``, or two members with the same parent-type
    relationship to the head. A domestic partner is not a spouse.

    Each state sets ``family_size_method``: ``individual_or_couple`` (the person plus a
    spouse) or ``extra_help`` (also counting the head's dependents, for the head or spouse
    only). A state choosing ``extra_help`` declares the member fields ``is_dependent()``
    reads.

    Data gaps (spec §5): Medicare part, Part B immunosuppressive enrollment, premium Part A
    buy-in, Medicaid eligibility as opposed to enrollment, in-kind support, the COLA
    transition months, the SSI income exclusions the screener doesn't collect, nonliquid and
    per-member resources, and married couples outside the head's family. Immigration is the
    program record's ``legal_status_required``, not this class. The poverty line comes from
    ``program.year``, the 48-state table, so a white label in Alaska or Hawaii would need its
    own.

    The spec is ``programs/cross_white_label/msp/base/msp_base_spec.md`` in program-ops.
    """

    family_size_method: ClassVar[FamilySizeMethod]
    evaluate_qdwi: ClassVar[bool] = False

    general_income_disregard: ClassVar[Decimal] = Decimal(20)
    earned_income_disregard: ClassVar[Decimal] = Decimal(65)
    need_based_income_types: ClassVar[tuple[str, ...]] = ("sSI", "cashAssistance", "cashAssistanceOther")
    excluded_unearned_types: ClassVar[tuple[str, ...]] = ("investment",)

    qmb_percent: ClassVar[Decimal] = Decimal("1.00")
    slmb_percent: ClassVar[Decimal] = Decimal("1.20")
    qi_percent: ClassVar[Decimal] = Decimal("1.35")
    qdwi_percent: ClassVar[Decimal] = Decimal("2.00")

    # 2026 figures: CMCS Informational Bulletin 2025-12-09.
    resource_limit: ClassVar[dict[bool, int]] = {False: 9_950, True: 14_910}
    qdwi_resource_limit: ClassVar[dict[bool, int]] = {False: 4_000, True: 6_000}
    qdwi_max_age: ClassVar[int] = 65
    # Substantial gainful activity, per month (2026), and the higher figure for blindness.
    sga_monthly: ClassVar[int] = 1_690
    sga_monthly_blind: ClassVar[int] = 2_830

    # 2026 monthly premiums: CMS fact sheet, 2026 Medicare Parts A & B Premiums and Deductibles.
    part_b_premium: ClassVar[Decimal] = Decimal("202.90")
    part_a_full_premium: ClassVar[Decimal] = Decimal(565)

    dependencies: ClassVar[tuple[str, ...]] = (
        "household_assets",
        "relationship",
        "insurance",
        "income_type",
        "income_amount",
        "income_frequency",
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        #: The group each eligible member qualified through, keyed by member id.
        self.member_routes: dict[int, Route] = {}
        self._relationship_map: Optional[dict] = None

    # ---------- the person and their spouse ----------

    def spouse_of(self, member: HouseholdMember) -> Optional[HouseholdMember]:
        if self._relationship_map is None:
            self._relationship_map = self.screen.relationship_map()

        partner_id = self._relationship_map.get(member.id)
        if partner_id is None:
            return None

        partner = next(m for m in self.screen.household_members.all() if m.id == partner_id)
        pair = {member.relationship, partner.relationship}
        if pair == {"headOfHousehold", "spouse"}:
            return partner
        if member.relationship == partner.relationship and member.relationship in PARENT_TYPE_RELATIONSHIPS:
            return partner

        return None

    def unit(self, member: HouseholdMember) -> list[HouseholdMember]:
        spouse = self.spouse_of(member)
        return [member] if spouse is None else [member, spouse]

    def family_size(self, member: HouseholdMember) -> int:
        size = len(self.unit(member))
        if self.family_size_method == "individual_or_couple":
            return size

        if not (member.is_head() or member.is_spouse()):
            return size

        unit_ids = {m.id for m in self.unit(member)}
        dependents = sum(1 for m in self.screen.household_members.all() if m.id not in unit_ids and m.is_dependent())
        return size + dependents

    # ---------- income ----------

    def countable_income(self, member: HouseholdMember) -> Decimal:
        """Monthly countable income of the member and their spouse, by SSI rules."""
        unit = self.unit(member)

        unearned = sum(
            (_exact(m.calc_gross_income("monthly", ["unearned"], exclude=self.excluded_unearned_types)) for m in unit),
            Decimal(0),
        )
        need_based = sum(
            (_exact(m.calc_gross_income("monthly", self.need_based_income_types)) for m in unit),
            Decimal(0),
        )
        earned = sum((_exact(m.calc_gross_income("monthly", ["earned"])) for m in unit), Decimal(0))

        general_used = min(self.general_income_disregard, unearned - need_based)
        countable_unearned = unearned - general_used
        remaining_disregard = self.general_income_disregard - general_used
        countable_earned = max(Decimal(0), earned - remaining_disregard - self.earned_income_disregard) / 2

        return countable_unearned + countable_earned

    def income_limit(self, percent: Decimal, family_size: int) -> int:
        """The monthly limit at ``percent`` of the poverty line, rounded up to the dollar."""
        annual_fpl = self.program.year.get_limit(family_size)
        return ceil(Fraction(percent) * annual_fpl / 12)

    # ---------- eligibility ----------

    def member_eligible(self, e: MemberEligibility) -> None:
        member = e.member
        route = self.route(member)
        e.condition(route is not None)
        if route is not None:
            self.member_routes[member.id] = route

    def route(self, member: HouseholdMember) -> Optional[Route]:
        """The group a member qualifies through, or None."""
        has_spouse = self.spouse_of(member) is not None
        assets = self.screen.household_assets if self.screen.household_assets is not None else 0
        countable = self.countable_income(member)
        family_size = self.family_size(member)

        if member.has_insurance_types(("medicare",)):
            if assets > self.resource_limit[has_spouse]:
                return None

            qmb_limit = self.income_limit(self.qmb_percent, family_size)
            slmb_limit = self.income_limit(self.slmb_percent, family_size)
            qi_limit = self.income_limit(self.qi_percent, family_size)

            if countable <= qmb_limit:
                return "qmb"
            if countable < slmb_limit:
                return "slmb"
            if countable < qi_limit and not member.has_insurance_types(("medicaid",)):
                return "qi"
            return None

        if self.evaluate_qdwi and self.qdwi_eligible(member, countable, family_size, has_spouse, assets):
            return "qdwi"

        return None

    def qdwi_eligible(
        self, member: HouseholdMember, countable: Decimal, family_size: int, has_spouse: bool, assets: int
    ) -> bool:
        """QDWI for a member who reports no Medicare. Run only where ``evaluate_qdwi`` is set."""
        age = member.calc_age()
        sga = self.sga_monthly_blind if member.visually_impaired else self.sga_monthly

        return (
            age is not None
            and age < self.qdwi_max_age
            and bool(member.has_disability())
            and member.calc_gross_income("monthly", ["earned"]) > sga
            and member.calc_gross_income("monthly", ["sSDisability"]) == 0
            and countable <= self.income_limit(self.qdwi_percent, family_size)
            and assets <= self.qdwi_resource_limit[has_spouse]
            and not member.has_insurance_types(("medicaid",))
        )

    # ---------- value ----------

    def member_value(self, member: HouseholdMember) -> int:
        monthly = self.part_a_full_premium if self.member_routes.get(member.id) == "qdwi" else self.part_b_premium
        return int((monthly * 12).quantize(Decimal(1), rounding=ROUND_HALF_UP))
