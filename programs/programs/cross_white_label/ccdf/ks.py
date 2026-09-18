"""Kansas Child Care Assistance Program (DCF child care subsidy)."""

from decimal import ROUND_HALF_UP, Decimal

from programs.framework.base import Eligibility, MemberEligibility, ProgramCalculator
import programs.framework.eligibility_messages as messages
from screener.models import EARNED_INCOME_TYPES, HouseholdMember

# Appendix C-18a provider rate county groupings. Group #3 is every county not named
# here. C-18/C-18a print "Greely" and "Pottawatomi"; the KS white label's spellings
# are used instead, because a literal transcription matches neither county and drops
# both into Group #3.
COUNTY_GROUP_1 = ("Johnson County",)
COUNTY_GROUP_2 = (
    "Butler County",
    "Douglas County",
    "Ellis County",
    "Geary County",
    "Greeley County",
    "Harvey County",
    "Jefferson County",
    "Leavenworth County",
    "Miami County",
    "Pottawatomie County",
    "Riley County",
    "Rush County",
    "Scott County",
    "Sedgwick County",
    "Seward County",
    "Shawnee County",
    "Wyandotte County",
)

# Appendix C-18 maximum hourly licensed-centre rates: (age band's inclusive upper
# bound in years, (Group #1, Group #2, Group #3)). Banding on `calc_age` is exactly
# equivalent to banding on the months C-18 prints, for the centre columns only --
# the licensed-home bands are not aligned this way.
#
# The rates are not monotonic across groups: Group #3's 36-59 month rate ($4.27)
# exceeds Group #2's ($4.13), as printed. Do not derive Group #3 by scaling Group #2.
CENTRE_HOURLY_RATES = (
    (0, (Decimal("7.33"), Decimal("6.28"), Decimal("6.28"))),  # 0-11 months
    (2, (Decimal("6.25"), Decimal("5.28"), Decimal("5.26"))),  # 12-35 months
    (4, (Decimal("5.51"), Decimal("4.13"), Decimal("4.27"))),  # 36-59 months
    (18, (Decimal("4.81"), Decimal("3.65"), Decimal("3.16"))),  # 60+ months
)

# Appendix F-1, effective 2026-05-01: one row per family size, ordered by band. Each
# entry is the band's *upper* bound on monthly gross income and the monthly Family
# Share Deduction that applies within it. A band's lower bound is one cent above the
# previous band's upper bound and the first starts at $0; the comparison is inclusive
# at the upper bound.
#
# The last band's upper bound is also that family size's 85% SMI income limit --
# these are not two tables but one read two ways, so `income_limit` derives the limit
# from this grid rather than restating it.
#
# The grid resolves Appendix F-1's printing slips; one is load-bearing, the family-of-3
# 170% bound, printed such that $3,870.01-$3,870.09 falls in no band at all. Do not
# transcribe F-1 literally and do not correct the source snapshots.
#
# Stopping at 8 is deliberate, not an incomplete transcription: F-1 publishes sizes
# **2 through 11**, but the screener's household size step validates `.lte(8)`, so no
# form-submitted screen can carry a larger one. `family_size` clamps above 8 rather
# than carrying three rows only the API path could reach. If that form cap is ever
# raised, add sizes 9-11 from the F-1 snapshot before the cap ships.
FAMILY_SHARE_DEDUCTIONS: dict[int, tuple[tuple[Decimal, int], ...]] = {
    2: (
        (Decimal("1803"), 0),
        (Decimal("1984"), 54),
        (Decimal("2164"), 60),
        (Decimal("2344"), 65),
        (Decimal("2525"), 70),
        (Decimal("2705"), 76),
        (Decimal("2885"), 81),
        (Decimal("3066"), 87),
        (Decimal("3246"), 92),
        (Decimal("3336"), 97),
        (Decimal("5439"), 167),
    ),
    3: (
        (Decimal("2277"), 0),
        (Decimal("2504"), 68),
        (Decimal("2732"), 75),
        (Decimal("2960"), 82),
        (Decimal("3187"), 89),
        (Decimal("3415"), 96),
        (Decimal("3643"), 102),
        (Decimal("3870"), 109),
        (Decimal("4098"), 116),
        (Decimal("4212"), 123),
        (Decimal("6719"), 211),
    ),
    4: (
        (Decimal("2750"), 0),
        (Decimal("3025"), 83),
        (Decimal("3300"), 91),
        (Decimal("3575"), 99),
        (Decimal("3850"), 107),
        (Decimal("4125"), 116),
        (Decimal("4400"), 124),
        (Decimal("4675"), 132),
        (Decimal("4950"), 140),
        (Decimal("5088"), 149),
        (Decimal("7998"), 254),
    ),
    5: (
        (Decimal("3223"), 0),
        (Decimal("3546"), 97),
        (Decimal("3868"), 106),
        (Decimal("4190"), 116),
        (Decimal("4513"), 126),
        (Decimal("4835"), 135),
        (Decimal("5157"), 145),
        (Decimal("5480"), 155),
        (Decimal("5802"), 164),
        (Decimal("5963"), 174),
        (Decimal("9278"), 298),
    ),
    6: (
        (Decimal("3697"), 0),
        (Decimal("4066"), 111),
        (Decimal("4436"), 122),
        (Decimal("4806"), 133),
        (Decimal("5175"), 144),
        (Decimal("5545"), 155),
        (Decimal("5915"), 166),
        (Decimal("6284"), 177),
        (Decimal("6654"), 189),
        (Decimal("6839"), 200),
        (Decimal("10558"), 342),
    ),
    7: (
        (Decimal("4170"), 0),
        (Decimal("4587"), 125),
        (Decimal("5004"), 138),
        (Decimal("5421"), 150),
        (Decimal("5838"), 163),
        (Decimal("6255"), 175),
        (Decimal("6672"), 188),
        (Decimal("7089"), 200),
        (Decimal("7506"), 213),
        (Decimal("7715"), 225),
        (Decimal("10798"), 386),
    ),
    8: (
        (Decimal("4643"), 0),
        (Decimal("5108"), 139),
        (Decimal("5572"), 153),
        (Decimal("6036"), 167),
        (Decimal("6501"), 181),
        (Decimal("6965"), 195),
        (Decimal("7429"), 209),
        (Decimal("7894"), 223),
        (Decimal("8358"), 237),
        (Decimal("8590"), 251),
        (Decimal("11038"), 430),
    ),
}

MIN_FAMILY_SIZE = min(FAMILY_SHARE_DEDUCTIONS)
MAX_FAMILY_SIZE = max(FAMILY_SHARE_DEDUCTIONS)


class KsCcap(ProgramCalculator):
    """
    Kansas Child Care Assistance Program (KEESM 2810-2840), the state's CCDF subsidy.

    Pays part of the cost of child care for a family with a child under 13 -- or 13
    through 18 and incapable of self-care -- whose income is within 85% of the State
    Median Income and whose countable resources are at or under $10,000. A non-TANF
    family must also have a personal need for care; only KEESM 2820's Maintain
    Employment reason is modelable, so every adult on the case must work an average
    of 20 hours a week at or above the federal minimum wage.

    A plain ``ProgramCalculator`` rather than a subclass of this family's ``Ccdf``
    base: that base wraps PolicyEngine's ``is_ccdf_eligible``, and this program is
    implemented from Kansas sources.

    The value is an **MFB-owned estimate, not an amount DCF publishes**. Kansas sets
    the benefit from its own maximum hourly rate rather than from what the family
    pays, so the estimate turns on two inputs DCF observes and the screener does not.

    **Provider type is pinned to a licensed centre**, which is the highest of the four
    rates Kansas pays -- in Johnson County for a preschooler, $5.51/hour against $4.23
    for a licensed home, $2.81 for an out-of-home relative and $2.42 for an in-home
    relative. C-18 sets centre and licensed-home rates at roughly the 75th percentile
    of surveyed market price, which makes the centre the defensible standard case, but
    no source says which type CCAP families actually use. A household using a relative
    is overstated by up to about 2.3x.

    **Authorized hours are derived rather than pinned** -- see `authorized_monthly_hours`.
    KEESM 7620 sets them from the adults' work schedule, which `hours_worked` records,
    so the block follows the household's reported hours where every adult on the case
    has them and falls back to part-time where one does not.

    The value also sums over every child meeting the age and relationship test, because
    which children a family requests care for is unobservable.

    Data gaps, in the exclusionary direction: seven of KEESM 2820's eight need reasons
    cannot be established from any screener field and are **not** assumed met, so a
    non-TANF household whose only reason is one of them -- post-secondary education,
    a Job Corps or teen-parent exemption, food assistance E&T, a social-services
    crisis, a foster-care case, KEHS/CC Partnership -- is screened out here. See the
    spec's Data Gaps preamble; the surface is deliberate and has no compensating
    control on the results page.
    """

    program_code = "ks_ccap"

    # `household_assets` is deliberately absent, and nullable: the spec commits this
    # calculator to a fall-open resource test, which declaring it would pre-empt --
    # a missing dependency drops the program from results before the test can run.
    # `household_size` is declared for the opposite reason. It is user-entered and
    # independent of the member list, so a member count is a different number rather
    # than a recovery of the missing one, and it keys both the income ceiling and the
    # family share deduction. Guessing it wrong denies an eligible household or
    # inflates an ineligible one's value, silently; being dropped from results says
    # so.
    dependencies = ["age", "relationship", "county", "household_size", "income_amount", "income_frequency"]

    RESOURCE_LIMIT = Decimal("10000")
    FEDERAL_MINIMUM_WAGE = Decimal("7.25")
    MINIMUM_WEEKLY_HOURS = 20
    # KEESM 7620's two authorized blocks, and the hours-needed figure that chooses
    # between them. `WEEKS_PER_MONTH` matches the factor the screener's own income
    # conversion uses, so a week of work and a week of care are counted alike.
    PART_TIME_HOURS = 129
    FULL_TIME_HOURS = 215
    HOURS_NEEDED_THRESHOLD = 108
    WEEKS_PER_MONTH = Decimal("4.35")

    # KEESM 4410's eligible-child set: the adults' own minor children, plus its
    # catch-all for other children in the household an adult on the case caretakes.
    # `relatedOther` carries that catch-all -- `il_ccap`'s six-value set omits it.
    child_relationships = (
        "child",
        "stepChild",
        "fosterChild",
        "grandChild",
        "sisterOrBrother",
        "stepSisterOrBrother",
        "relatedOther",
    )

    # KEESM 4410 puts the head and their spouse or partner on the case. Any other
    # adult -- a grandparent, an adult sibling, a roommate -- counts toward family
    # size and is never activity-tested.
    tested_relationships = ("headOfHousehold", "spouse", "domesticPartner")

    def member_eligible(self, e: MemberEligibility):
        e.condition(self.is_eligible_child(e.member))

    def household_eligible(self, e: Eligibility):
        # KEESM 2831: a nuclear family with a TANF recipient is served under TANF
        # Child Care, which states no hours or wage requirement, waives the income
        # test (KEESM 7540) and exempts the resource limit (KEESM 5140). Treating
        # receipt as establishing personal need is over-inclusive by design -- KEESM
        # 2831 still requires one of its listed need reasons and MFB cannot see which.
        if self.screen.has_base_benefit("tanf"):
            e.condition(True, messages.presumed_eligibility())
            return

        # Criterion 3 -- personal need.
        e.condition(self.meets_personal_need())

        # Criterion 4 -- income within the family size's 85% SMI limit.
        income = self.countable_monthly_income()
        limit = self.income_limit()
        e.condition(income <= limit, messages.income(int(income), int(limit)))

        # Criterion 5 -- countable resources.
        e.condition(self.resources_within_limit(), messages.assets(int(self.RESOURCE_LIMIT)))

    def is_eligible_child(self, member: HouseholdMember) -> bool:
        """Criterion 1. Also the set the value sums over, so the two cannot drift."""
        if member.relationship not in self.child_relationships:
            return False

        # Month-granular: the under-13 boundary falls on the first of the birth
        # month, not the birthday.
        age = member.calc_age()
        if age is None:
            return False

        if age < 13:
            return True

        # KEESM 2810 extends eligibility through 18 for a child physically or
        # mentally incapable of self-care. Court supervision, the other sourced
        # route in, has no screener field, so this branch is disability-only.
        return age <= 18 and bool(member.has_disability())

    def eligible_children(self) -> list[HouseholdMember]:
        return [member for member in self.screen.household_members.all() if self.is_eligible_child(member)]

    def meets_personal_need(self) -> bool:
        """
        KEESM 2820's Maintain Employment reason, the one modelable pathway.

        The other seven reasons cannot be established from any screener field and
        are not assumed met: falling open wherever an unobservable pathway might
        apply would remove this criterion's screening power entirely.
        """
        for member in self.screen.household_members.all():
            if member.relationship not in self.tested_relationships:
                continue
            if not self.adult_meets_activity_test(member):
                return False

        return True

    def adult_meets_activity_test(self, member: HouseholdMember) -> bool:
        """
        KEESM 2835's two halves for one adult on the case: employed an average of at
        least 20 hours a week, **and** earning at least the federal minimum wage.

        The halves carry different exceptions. The hours requirement is excused for
        an adult not capable of meeting it due to a documented condition; the wage
        floor carries no such exception in any captured source.
        """
        exempt_from_hours = bool(member.has_disability())

        streams = list(member.income_streams.all())
        earned = [stream for stream in streams if stream.type in EARNED_INCOME_TYPES]

        if not earned:
            # Observably not employed rather than unevaluable -- KEESM 2810 denies
            # the household where one parent works and the other does not, the
            # non-employed parent being expected to provide the care.
            return exempt_from_hours

        # `hours_worked` is populated only on hourly-frequency streams, so neither
        # half is derivable for a salaried, weekly, biweekly or yearly earner, and
        # such an adult is not screened out on either. `TotalHoursWorkedDependency`
        # is deliberately not reused: its imputation for non-hourly streams fixes the
        # implied wage at exactly the federal minimum, which would make the wage
        # floor circular, and it floors reported hours at 40 for members aged 16 and
        # over, which would make the 20-hour test unfailable.
        hourly = self.hourly_earned_streams(member)
        if not hourly:
            return True

        total_hours = sum(stream.hours_worked for stream in hourly)
        if not exempt_from_hours and total_hours < self.MINIMUM_WEEKLY_HOURS:
            return False

        # The floor is the adult's average across their hourly streams, not a test of
        # each stream on its own: a second job below the minimum does not sink an
        # adult whose employment as a whole clears it. With one stream this is
        # exactly that stream's rate.
        wages = sum((stream.amount * stream.hours_worked for stream in hourly), Decimal(0))
        return wages / total_hours >= self.FEDERAL_MINIMUM_WAGE

    @staticmethod
    def hourly_earned_streams(member: HouseholdMember) -> list:
        """
        The member's hourly-frequency earned streams that carry usable hours.

        `hours_worked` is populated only at hourly frequency, so this is the whole
        of what the screener can say about anyone's schedule. A zero or null is
        dropped rather than counted: it cannot be averaged over and reads as
        unstated rather than as an assertion of no hours.
        """
        return [
            stream
            for stream in member.income_streams.all()
            if stream.type in EARNED_INCOME_TYPES and stream.frequency == "hourly" and stream.hours_worked
        ]

    def tested_adults(self) -> list[HouseholdMember]:
        """The KEESM 4410 adults on the case: the head plus a spouse or partner."""
        return [
            member for member in self.screen.household_members.all() if member.relationship in self.tested_relationships
        ]

    def authorized_monthly_hours(self) -> int:
        """
        KEESM 7620's authorized block: 129 hours where the hours needed are 108 or
        fewer, 215 where they are more.

        7620 sets hours needed from the adults' weekly work schedule (plus travel)
        and the child's school schedule. The work schedule is the one input the
        screener records, on `hours_worked`, so the block is derived from it rather
        than pinned — but only when **every** adult on the case has derivable hours.
        A salaried, weekly or biweekly earner carries no `hours_worked` at all, so
        one such adult makes the household's schedule unreadable and the estimate
        falls back to the part-time block.

        Care is needed only while every adult on the case is away, so the household's
        hours track the **least**-working adult: KEESM 2810 denies the household
        where one parent works and the other does not, the non-employed parent being
        expected to provide the care. Without actual schedules the overlap between
        two adults cannot exceed the shorter of them, so the minimum is that
        overlap's upper bound — staggered shifts need less care than this allows,
        never more.

        Two sourced inputs remain unobservable and pull opposite ways: travel time,
        which 7620 counts and which raises hours, and the child's school schedule,
        which lowers them for a school-age child. Neither is collected.
        """
        adults = self.tested_adults()
        if not adults:
            return self.PART_TIME_HOURS

        weekly_hours = []
        for adult in adults:
            hourly = self.hourly_earned_streams(adult)
            if not hourly:
                # One unreadable schedule makes the household's unreadable, because
                # the block turns on the minimum across all of them.
                return self.PART_TIME_HOURS
            weekly_hours.append(sum(stream.hours_worked for stream in hourly))

        hours_needed = min(weekly_hours) * self.WEEKS_PER_MONTH

        # 7620's own wording -- 129 at "108 or less", 215 at "more than 108" -- but the
        # boundary is unreachable and so untestable: `hours_worked` is an integer and
        # 108 / 4.35 is 24.83, so no whole week of work lands exactly on 108. The
        # turnover sits between 24 hours (104.4) and 25 (108.75). `>=` here would
        # behave identically; it is written `>` to match the source, not because a
        # household can tell the difference.
        return self.FULL_TIME_HOURS if hours_needed > self.HOURS_NEEDED_THRESHOLD else self.PART_TIME_HOURS

    def countable_monthly_income(self) -> Decimal:
        """
        KEESM 7540's nonexempt gross monthly income, quantised to the cent.

        `calc_gross_income` cannot express this: its `exclude` argument filters income
        *types*, and both exemptions below turn on the **earner** instead.
        """
        total = Decimal(0)
        for member in self.screen.household_members.all():
            if self.income_is_exempt(member):
                continue
            for stream in member.income_streams.all():
                total += stream.monthly()

        # Quantise before any Appendix F-1 comparison, and read the quantised figure
        # for both the band lookup and the limit test. `_hour_to_month` multiplies by
        # the float-derived `Decimal(4.35)`, which is strictly below 4.35, so without
        # this every hourly-derived amount lands a fraction of a cent low and no
        # household can sit exactly on a published bound.
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def income_is_exempt(self, member: HouseholdMember) -> bool:
        # KEESM 6410 exempts the income of an SSI *recipient* in full, not merely the
        # SSI payment -- their wages leave countable income as well. Read per member:
        # `has_base_benefit("ssi")` is household-level and cannot say whose income to
        # exempt.
        if self.receives_ssi(member):
            return True

        age = member.calc_age()
        if age is None:
            return False

        # KEESM 6410 exempts a child's earnings under 18, or under 19 while working
        # toward a diploma or its equivalent. `student` is nullable and a null reads
        # as True, the inclusive direction. The sourced exception -- a child legally
        # responsible for another member of the nuclear family -- is unobservable.
        if age < 18:
            return True

        return age < 19 and (member.student is None or member.student)

    @staticmethod
    def receives_ssi(member: HouseholdMember) -> bool:
        return any(stream.type == "sSI" for stream in member.income_streams.all())

    def resources_within_limit(self) -> bool:
        """Criterion 5. KEESM 5140's $10,000 limit, inclusive at exactly $10,000."""
        # KEESM 5140 exempts the limit where the only children receiving child care
        # assistance also receive SSI. Tested per eligible child, never through
        # `has_base_benefit("ssi")`, which is set from *any* member's SSI and would
        # waive the limit off an SSI parent.
        children = self.eligible_children()
        if children and all(self.receives_ssi(child) for child in children):
            return True

        assets = self.screen.household_assets
        if assets is None:
            # Nullable, and a household that simply skipped the question is not
            # screened out on it.
            return True

        return Decimal(assets) <= self.RESOURCE_LIMIT

    def family_size(self) -> int:
        """
        KEESM 4410's nuclear family, proxied by the screen-wide household size.

        The error direction is not uniform: a non-caretaker grandparent, an adult
        sibling or a roommate sits outside the nuclear family but inside the count,
        raising the income limit and adding income at the same time.

        This is the same number for the income limit and for the Family Share
        Deduction -- never compute the two separately. It is user-entered and
        independent of the member list, so neither `num_children` nor a member count
        stands in for it: a null is a declared dependency and drops the program from
        results rather than being guessed at.
        """
        # Both ends are unreachable through the screener: the form validates `.lte(8)`,
        # and below 2 cannot arise because criterion 1 requires an eligible child, whose
        # relationship is never `headOfHousehold`. The clamp is for the API path only.
        # Above 8 it is a deliberate ceiling rather than a missing row -- see the note
        # on FAMILY_SHARE_DEDUCTIONS.
        return min(max(self.screen.household_size, MIN_FAMILY_SIZE), MAX_FAMILY_SIZE)

    def income_limit(self) -> Decimal:
        """
        The 85% SMI ceiling for the family size.

        Read off the top Family Share Deduction band's upper bound rather than
        restated, because they are the same published figure. DCF's 2021 memo set
        child care eligibility at 250% FPL, but SMI growth has overtaken it and every
        2026 limit now sits above 250%; there is no second FPL gate.
        """
        return FAMILY_SHARE_DEDUCTIONS[self.family_size()][-1][0]

    def family_share_deduction(self) -> Decimal:
        """One Appendix F-1 deduction for the household, not one per child."""
        # KEESM 2835 assigns no family share to a TANF household. The four other
        # sourced $0 cases -- the post-TANF window, food assistance E&T, the social
        # services reason and KEHS/CC Partnership -- are unscreenable, so the
        # deduction is assessed normally for them.
        if self.screen.has_base_benefit("tanf"):
            return Decimal(0)

        income = self.countable_monthly_income()
        bands = FAMILY_SHARE_DEDUCTIONS[self.family_size()]
        for upper_bound, deduction in bands:
            if income <= upper_bound:
                return Decimal(deduction)

        # Above the top band the household is ineligible on criterion 4, so this is
        # reachable only if a value is asked for a household that failed it.
        return Decimal(bands[-1][1])

    def centre_hourly_rate(self, member: HouseholdMember) -> Decimal:
        group_index = self.county_group_index()
        age = member.calc_age()

        for max_age, rates in CENTRE_HOURLY_RATES:
            if age <= max_age:
                return rates[group_index]

        return CENTRE_HOURLY_RATES[-1][1][group_index]

    def county_group_index(self) -> int:
        """
        Appendix C-18a's rate group, as an index into a `CENTRE_HOURLY_RATES` row.

        KEESM 10240 keys the rate on the **provider's** county. MFB observes only the
        family's and uses it as a proxy.
        """
        county = self.screen.county

        if county in COUNTY_GROUP_1:
            return 0
        if county in COUNTY_GROUP_2:
            return 1

        return 2

    def household_value(self) -> int:
        """
        The whole annual figure, returned here with no member values, because both
        `max` operations below are on the household total. `il_ccap` splits the same
        shape across `member_value` and a negative `household_value`; in that shape
        neither clamp can be expressed.
        """
        hours = self.authorized_monthly_hours()
        gross = sum(
            (self.centre_hourly_rate(child) * hours for child in self.eligible_children()),
            Decimal(0),
        )

        # The policy clamp. DCF genuinely pays nothing to a household whose family
        # share exceeds its benefit.
        monthly = max(gross - self.family_share_deduction(), Decimal(0))

        # Truncated here rather than left to `screener/views.py`, which truncates only
        # the payload's `estimated_value` -- the results card reads `household_value`
        # and formats it with `maximumFractionDigits: 0`, which rounds.
        annual = int(monthly * 12)

        # A visibility floor, not a claim that Kansas pays $1: the frontend's
        # `programValue > 0` filter drops an eligible $0 program from the results page
        # entirely, so the household would see no card at all rather than an eligible
        # one worth nothing.
        return max(1, annual)
