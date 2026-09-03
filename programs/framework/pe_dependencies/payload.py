"""
Assembles the PolicyEngine request payload from a Screen.

This is the Screen -> PolicyEngine household-shape translation: people keyed by member id,
tax units, marital units, SPM units, families. No HTTP happens here; sending the payload is
the client's job (integrations/clients/policyengine/policy_engine.py).

Version resolution is read from the client because the resolved version does two things
here: it goes into the request body, and its comparable form gates which inputs are sent at
all (see version_supports). calc_pe_eligibility resolves it once and threads it through as
`resolved_version` so the version deciding which programs are readable is the one deciding
which fields are sent.
"""

import copy
from dataclasses import dataclass, field as dataclass_field
from typing import Dict, List, Optional, Tuple

from screener.models import Screen

from programs.framework.pe_base import PolicyEngineCalulator
from programs.framework.pe_dependencies.base import ConflictingDependencyError, Member, TaxUnit
from programs.framework.pe_dependencies.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT
from integrations.clients.policyengine import versions as pe_versions

#: How many PolicyEngine requests one screen may be split into before we stop splitting and
#: start dropping programs. Each bucket is a separate HTTP round trip, and the gunicorn
#: worker timeout (120s) against PolicyEngine's read timeout (30s) leaves room for a handful.
#: Only screens that actually carry a disagreement split at all, and today exactly one
#: program wants a value another program contradicts, so 3 is slack rather than a budget.
#:
#: This bounds the request *count* only. Three slow-but-not-failing calls would outlast the
#: worker timeout and cost the whole response, so the dispatcher holds a wall-clock budget
#: too (`PE_BUCKET_TIME_BUDGET_SECONDS` in the PolicyEngine client) and stops early when it
#: is spent.
MAX_PAYLOAD_BUCKETS = 3

#: Dependency classes known to write one payload slot with different values, as the set of
#: class names taking part in each such disagreement.
#:
#: A split between exactly these is structural rather than a mistake: age on the screening
#: date and age at the end of the claim year are both correct, for different rules, and a
#: large recurring share of Missouri screens carries both. Reporting every one of them as a
#: Sentry warning would bury the disagreements that mean something, so these are logged
#: instead (see `_report_conflicts`). Any other combination stays a warning.
EXPECTED_CONFLICTING_DEPENDENCIES: Tuple[frozenset, ...] = (
    frozenset({"AgeDependency", "AgeAtEndOfClaimYearDependency"}),
)


@dataclass(frozen=True)
class Slot:
    """One addressable place in the payload: ``household[unit][sub_unit][field][period]``.

    This is the granularity a disagreement happens at. Two programs sending different values
    for the same field at the same period *for the same member* conflict; the same field at
    two periods, or for two members, does not.
    """

    unit: str
    sub_unit: str
    field: str
    period: str


@dataclass(frozen=True)
class Contribution:
    """One program's answer for one slot. `program_index` indexes the `programs` list passed
    to `build_pe_input`, which is how a contribution is traced back to the calculator that
    made it without requiring calculators to be hashable."""

    slot: Slot
    value: object
    program_index: int

    #: Name of the dependency class that produced this value, for telling an expected
    #: disagreement from an unexpected one (see EXPECTED_CONFLICTING_DEPENDENCIES). Defaults
    #: to empty for contributions built by tests, which assert on values not on sources.
    dependency: str = ""


@dataclass
class Bucket:
    """The programs answered by one PolicyEngine request, and how that request's payload
    differs from the union payload.

    `overrides` is empty for the first bucket: its payload *is* the union payload, which is
    byte-for-byte what a screen sent before payload splitting existed. Later buckets are the
    same payload with only the contradicted slots rewritten, so a program that disagrees
    about one field still sees every other input the screen produced."""

    program_indexes: List[int]
    overrides: Dict[Slot, object] = dataclass_field(default_factory=dict)


@dataclass
class PayloadPlan:
    """Everything payload assembly decided: the union payload, how the screen's programs were
    split across requests, which programs were dropped outright, and a description of each
    disagreement for the log."""

    payload: dict
    buckets: List[Bucket]
    dropped_program_indexes: List[int] = dataclass_field(default_factory=list)
    conflicts: List[str] = dataclass_field(default_factory=list)

    #: Programs dropped because they contradict *themselves* — two of their own dependencies
    #: write one slot with different values, so no single payload can serve them. Also listed
    #: in `dropped_program_indexes`; kept apart because it means a program's declared inputs
    #: are wrong, not that a screen ran out of requests.
    self_conflicting_program_indexes: List[int] = dataclass_field(default_factory=list)

    #: The subset of `conflicts` whose dependency classes are not a known pairing, i.e. the
    #: disagreements worth raising rather than logging.
    unexpected_conflicts: List[str] = dataclass_field(default_factory=list)


def _has_gated_input(programs: List[PolicyEngineCalulator]) -> bool:
    """True if any input/output in these programs is version-gated (has a
    min_pe_version or max_pe_version). Lets us skip resolving the PE version when
    nothing in the request depends on it."""
    for program in programs:
        for Data in program.pe_inputs + program.pe_outputs:
            if getattr(Data, "min_pe_version", ()) or getattr(Data, "max_pe_version", ()):
                return True
    return False


def _resolve_comparable_version(programs: List[PolicyEngineCalulator], version: str) -> Optional[tuple]:
    """Tuple form of `version`, for gating which inputs and outputs may be sent.

    The "current" alias has no comparable form of its own, so resolve what it points at from
    PolicyEngine's /versions/us — otherwise a min_pe_version floor could never be met and
    gated fields would be withheld forever. Stays None if PolicyEngine is unreachable, keeping
    the conservative withhold-gated behavior. Only resolves when the request carries a gated
    field, since most don't."""
    comparable_version = pe_versions.to_comparable_pe_version(version)
    if comparable_version is None and _has_gated_input(programs):
        comparable_version = pe_versions.resolve_unpinned_comparable_version()
    return comparable_version


def _period_for(program, Data) -> str:
    """The period one variable is sent at.

    `program` is normally a calculator instance, and this defers to its own `period_for`.
    Many of the older payload-shape tests pass the calculator *class* instead; `pe_period`
    is a property, so on a class it yields the property object rather than a period. Those
    tests assert on which fields are sent and read the period key back off the dict, so that
    has always worked — keep it working rather than making this the place that migration
    happens.
    """
    if isinstance(program, PolicyEngineCalulator):
        return program.period_for(Data)

    if Data in program.pe_monthly_outputs:
        return f"{program.pe_period}-{program.pe_period_month}"

    return program.pe_period


def pe_input(
    screen: Screen,
    programs: List[PolicyEngineCalulator],
    pe_version: Optional[str] = None,
    resolved_version: Optional[tuple[str, Optional[tuple]]] = None,
):
    """
    Generate Policy Engine API request from the list of programs.

    The union payload: every program's inputs in one household, which is the only payload
    there is for a screen whose programs all agree. Callers that need to know about
    disagreements — and therefore about the extra requests they imply — want
    `build_pe_input` instead.

    `resolved_version` is the caller's already-resolved (version string, comparable version)
    pair, passed by `calc_pe_eligibility` so the version deciding which programs are readable
    is the one deciding which fields are sent. Direct callers may omit it.
    """
    return build_pe_input(screen, programs, pe_version=pe_version, resolved_version=resolved_version).payload


def build_pe_input(
    screen: Screen,
    programs: List[PolicyEngineCalulator],
    pe_version: Optional[str] = None,
    resolved_version: Optional[tuple[str, Optional[tuple]]] = None,
    max_buckets: int = MAX_PAYLOAD_BUCKETS,
) -> PayloadPlan:
    """Build the PolicyEngine payload(s) for these programs, splitting where they disagree.

    One shared household serves every program in a request, so two programs that want
    different values for the same field, period and member cannot both be served by one
    payload. That used to raise out of here uncaught and 500 the whole eligibility response
    over a single program's disagreement. Now the disagreement is resolved by splitting: the
    value most programs asked for goes in the union payload, and the programs
    that wanted something else are answered by a follow-up request carrying the same payload
    with only the contradicted slots rewritten.

    Splitting is decided on *values*, not on which dependency classes a program declares, so
    two programs that could disagree but happen to agree for this household still share one
    request. `max_buckets` bounds how far this goes; past it the remaining programs are
    dropped and reported rather than served.
    """
    programs = list(programs)

    # Two values from one resolved version, for two consumers:
    #   version (string)            -> version to send in the PE API request body. Always
    #                                   set: the DB pin, the test override, or the literal
    #                                   "current" alias (household.api resolves it server-side).
    #   comparable_version (tuple)  -> tuple representation to gate which inputs are sent
    #
    # Send the alias, never the concrete resolution: household.api serves only what its
    # aliases currently point at and 422s any other exact version, so a resolved-then-stale
    # string would hard-fail every request once PolicyEngine promotes a release.
    if resolved_version is not None:
        version, comparable_version = resolved_version
    else:
        version = pe_versions.determine_pe_version(pe_version)
        comparable_version = _resolve_comparable_version(programs, version)

    raw_input, members, main_tax_members, secondary_tax_members, relationship_map = _household_shape(screen)

    contributions = _collect_contributions(
        screen,
        programs,
        members,
        main_tax_members,
        secondary_tax_members,
        relationship_map,
        comparable_version,
    )

    # A program whose own two dependencies want different values for one slot can be served
    # by no payload at all, so it is dropped before partitioning rather than left to lose
    # every pass: partitioning would force it back in on its own to guarantee progress, and
    # `_values_for` would then raise — costing every PolicyEngine program on the screen its
    # result over one program's input list. Its contributions go too, so nothing arbitrarily
    # picks one of its two values for a slot nobody left will read.
    self_conflicting = _self_conflicting_indexes(contributions)
    servable = [contribution for contribution in contributions if contribution.program_index not in self_conflicting]

    program_indexes = [index for index in range(len(programs)) if index not in self_conflicting]
    grouped, unserved = _partition(servable, program_indexes, max_buckets)
    dropped = sorted(unserved + sorted(self_conflicting))

    # The union payload takes the first bucket's value wherever the two differ. Every
    # contradicted slot is written by the first bucket by construction — the majority group
    # is what defines that bucket — so a slot missing from its values is a slot nobody
    # disagreed about, and there the contribution's own value is the only one there is.
    union_values = _values_for(servable, grouped[0]) if grouped else {}
    written = _write_union(raw_input, servable, union_values)

    buckets = [Bucket(program_indexes=grouped[0])] if grouped else []
    for bucket_indexes in grouped[1:]:
        bucket_values = _values_for(servable, bucket_indexes)
        buckets.append(
            Bucket(
                program_indexes=bucket_indexes,
                # Compared against what the union payload actually holds, not against the
                # first bucket's preferences: a slot no first-bucket program contributed
                # was written from whichever contribution reached it first, and a later
                # bucket still has to correct that.
                overrides={slot: value for slot, value in bucket_values.items() if written.get(slot, value) != value},
            )
        )

    conflicts, unexpected_conflicts = _describe_conflicts(contributions, programs, grouped, dropped)

    return PayloadPlan(
        payload=_finalize(raw_input, version, len(secondary_tax_members) == 0),
        buckets=buckets,
        dropped_program_indexes=dropped,
        conflicts=conflicts,
        self_conflicting_program_indexes=sorted(self_conflicting),
        unexpected_conflicts=unexpected_conflicts,
    )


def bucket_payload(plan: PayloadPlan, bucket: Bucket) -> dict:
    """The payload for one bucket: the union payload with that bucket's slots rewritten.

    Carrying the whole union rather than rebuilding from the bucket's own programs is
    deliberate. A program in a later bucket disagrees about one field; it should still see
    every other input the screen produced, exactly as it did when all programs shared one
    payload. It also makes the first bucket's payload identical to the pre-split one, so a
    disagreement changes results only for the programs that caused it.
    """
    if not bucket.overrides:
        return plan.payload

    payload = copy.deepcopy(plan.payload)
    for slot, value in bucket.overrides.items():
        # Only slots already in the union payload are overridden (see build_pe_input), so
        # every level of this path exists -- except a secondary tax unit dropped for being
        # empty, which no member contributes to anyway.
        unit = payload["household"].get(slot.unit, {}).get(slot.sub_unit)
        if unit is None:
            continue
        unit.setdefault(slot.field, {})[slot.period] = value

    return payload


def _household_shape(screen: Screen):
    """The household skeleton: units, their members, and the marital pairing. Independent of
    which programs are being asked about, so it is built once per screen."""
    raw_input = {
        "household": {
            "people": {},
            "tax_units": {
                MAIN_TAX_UNIT: {
                    "members": [],
                },
                SECONDARY_TAX_UNIT: {
                    "members": [],
                },
            },
            "families": {"family": {"members": []}},
            "households": {"household": {"members": []}},
            "spm_units": {
                "spm_unit": {
                    "members": [],
                }
            },
            "marital_units": {},
        }
    }

    # order_by("id") is load-bearing, not tidiness: the payload lists every unit's members
    # in iteration order, and the cassette matcher compares request bodies exactly. Without
    # it Postgres picks the order, so the same household can serialize differently between
    # runs and a recorded cassette stops matching — the request then goes to the live API.
    members = screen.household_members.all().order_by("id")
    relationship_map = screen.relationship_map()

    main_tax_members = []
    secondary_tax_members = []
    for member in members:
        member_id = str(member.id)
        household = raw_input["household"]

        household["families"]["family"]["members"].append(member_id)
        household["households"]["household"]["members"].append(member_id)
        household["spm_units"]["spm_unit"]["members"].append(member_id)
        household["people"][member_id] = {}

        if member.is_in_tax_unit():
            household["tax_units"][MAIN_TAX_UNIT]["members"].append(member_id)
            main_tax_members.append(member)
        else:
            household["tax_units"][SECONDARY_TAX_UNIT]["members"].append(member_id)
            secondary_tax_members.append(member)

    already_added = set()
    for member_1, member_2 in relationship_map.items():
        if member_1 in already_added or member_2 in already_added or member_1 is None or member_2 is None:
            continue

        marital_unit = (str(member_1), str(member_2))
        raw_input["household"]["marital_units"]["-".join(marital_unit)] = {"members": marital_unit}
        already_added.add(member_1)
        already_added.add(member_2)

    return raw_input, members, main_tax_members, secondary_tax_members, relationship_map


def _collect_contributions(
    screen: Screen,
    programs: List[PolicyEngineCalulator],
    members,
    main_tax_members,
    secondary_tax_members,
    relationship_map,
    comparable_version: Optional[tuple],
) -> List[Contribution]:
    """Every value every program wants to send, in the order the payload is written.

    Values are computed before anything is written so disagreements can be resolved knowing
    all of them, rather than by whichever program happened to be iterated first. The order is
    preserved because it decides key order in the request body, which the cassette matcher
    compares exactly.
    """
    contributions: List[Contribution] = []

    for index, program in enumerate(programs):
        for Data in program.pe_inputs + program.pe_outputs:
            # Skip inputs the resolved model version doesn't define yet — sending an
            # unknown variable 400s the whole request (e.g. meets_ssi_disability_criteria
            # on 1.691.1). comparable_version is the concrete "current" resolved above
            # when this request carries a version-gated input; if PE was unreachable it
            # stays None and version_supports conservatively withholds min-gated inputs.
            if not pe_versions.version_supports(
                comparable_version,
                getattr(Data, "min_pe_version", ()),
                getattr(Data, "max_pe_version", ()),
            ):
                continue

            # Per variable, not per program: a program can read an annual value and a
            # monthly one in the same request (see PolicyEngineCalulator.period_for).
            period = _period_for(program, Data)

            if issubclass(Data, Member):
                for member in members:
                    data = Data(screen, member, relationship_map, period=period)
                    contributions.append(
                        Contribution(
                            Slot(data.unit, str(member.id), data.field, period),
                            data.value(),
                            index,
                            Data.__name__,
                        )
                    )
            elif issubclass(Data, TaxUnit):
                # split the household into the main and secondary tax unit.
                for sub_unit, unit_members in (
                    (MAIN_TAX_UNIT, main_tax_members),
                    (SECONDARY_TAX_UNIT, secondary_tax_members),
                ):
                    data = Data(screen, unit_members, relationship_map, period=period)
                    contributions.append(
                        Contribution(Slot(data.unit, sub_unit, data.field, period), data.value(), index, Data.__name__)
                    )
            else:
                data = Data(screen, members, relationship_map, period=period)
                contributions.append(
                    Contribution(Slot(data.unit, data.sub_unit, data.field, period), data.value(), index, Data.__name__)
                )

    return contributions


def _group_by_value(contributions: List[Contribution]) -> Dict[Slot, List[Tuple[object, List[int]]]]:
    """Per slot, the distinct values wanted and which programs wanted each, first seen first.

    Distinctness is plain ``==``, matching what the single-pass write used to compare, so
    this recognises exactly the disagreements that used to raise and no others. A program
    naming the same dependency twice contributes twice; callers counting programs dedupe.
    """
    groups: Dict[Slot, List[Tuple[object, List[int]]]] = {}

    for contribution in contributions:
        slot_groups = groups.setdefault(contribution.slot, [])
        for value, indexes in slot_groups:
            if value == contribution.value:
                indexes.append(contribution.program_index)
                break
        else:
            slot_groups.append((contribution.value, [contribution.program_index]))

    return groups


def _self_conflicting_indexes(contributions: List[Contribution]) -> set:
    """Programs that want two different values for one slot all by themselves.

    `pe_inputs` lists are assembled from shared dependency groups, so a program can end up
    declaring two classes that write the same field — `AgeDependency` alongside
    `AgeAtEndOfClaimYearDependency`, say. Two *programs* shaped that way split into two
    requests and both get served. One *program* shaped that way cannot be served at all:
    both values would have to land in the same payload. It is a bug in that program's
    declared inputs, so it is dropped and reported rather than allowed to fail the screen.
    """
    values: Dict[Tuple[int, Slot], object] = {}
    conflicting: set = set()

    for contribution in contributions:
        key = (contribution.program_index, contribution.slot)
        if key in values:
            if values[key] != contribution.value:
                conflicting.add(contribution.program_index)
            continue

        values[key] = contribution.value

    return conflicting


def _partition(
    contributions: List[Contribution],
    program_indexes: List[int],
    max_buckets: int,
) -> Tuple[List[List[int]], List[int]]:
    """Split programs into groups that can each be served by one payload.

    Each pass keeps the programs that agree with the majority on every slot and defers the
    rest to the next pass, so every group is internally consistent by construction. The
    majority wins because that loses the fewest programs if splitting has to stop; it is not
    a claim that the majority is right. Ties go to the program iterated first, which makes
    the outcome depend on registry order only when the counts are equal.

    Returns the groups and, if `max_buckets` is reached first, the programs left unserved.
    """
    groups: List[List[int]] = []
    remaining = list(program_indexes)

    while remaining:
        if len(groups) >= max_buckets:
            return groups, remaining

        remaining_set = set(remaining)
        losers: set = set()
        for slot_groups in _group_by_value([c for c in contributions if c.program_index in remaining_set]).values():
            if len(slot_groups) < 2:
                continue

            winner = max(range(len(slot_groups)), key=lambda i: len(set(slot_groups[i][1])))
            for position, (_, indexes) in enumerate(slot_groups):
                if position != winner:
                    losers.update(indexes)

        kept = [index for index in remaining if index not in losers]

        # A program can win one slot and lose another, so in principle every program in a
        # pass can be a loser. Keeping the first one guarantees the pass makes progress and
        # the loop terminates; without it a screen shaped that way would hang. A group of one
        # is always servable: programs that contradict themselves are dropped before
        # partitioning, so no single program holds two values for one slot.
        if not kept:
            kept = remaining[:1]

        groups.append(kept)
        kept_set = set(kept)
        remaining = [index for index in remaining if index not in kept_set]

    return groups, []


def _values_for(contributions: List[Contribution], program_indexes: List[int]) -> Dict[Slot, object]:
    """What these programs, taken together, want in each slot.

    `_partition` guarantees they agree, so a disagreement here is a bug in the partition
    rather than a fact about the screen — hence the raise rather than a resolution.
    """
    indexes = set(program_indexes)
    values: Dict[Slot, object] = {}

    for contribution in contributions:
        if contribution.program_index not in indexes:
            continue

        if contribution.slot in values:
            if values[contribution.slot] != contribution.value:
                raise ConflictingDependencyError(
                    contribution.slot.field,
                    contribution.value,
                    values[contribution.slot],
                    period=contribution.slot.period,
                    member=contribution.slot.sub_unit,
                )
            continue

        values[contribution.slot] = contribution.value

    return values


def _write_union(
    raw_input: dict, contributions: List[Contribution], union_values: Dict[Slot, object]
) -> Dict[Slot, object]:
    """Write every contributed slot into the household, taking `union_values` where it has an
    opinion, and report what was written.

    Fields land in first-contribution order, which is the key order the pre-split payload had
    and the cassette matcher compares exactly. Note the *value* does not depend on which
    contribution arrived first, only the key order does.
    """
    written: Dict[Slot, object] = {}

    for contribution in contributions:
        slot = contribution.slot
        if slot in written:
            continue

        unit = raw_input["household"][slot.unit][slot.sub_unit]
        if slot.field not in unit:
            unit[slot.field] = {}

        written[slot] = union_values.get(slot, contribution.value)
        unit[slot.field][slot.period] = written[slot]

    return written


def _finalize(raw_input: dict, version: str, secondary_tax_unit_is_empty: bool) -> dict:
    # delete the second tax unit if it is empty because PE can't handle empty tax units
    if secondary_tax_unit_is_empty:
        del raw_input["household"]["tax_units"][SECONDARY_TAX_UNIT]

    # Always inject the version (override > DB pin > "current"): determine_pe_version
    # never returns None, so a version is always sent.
    raw_input["version"] = version

    return raw_input


def _program_label(program) -> str:
    code = getattr(program, "program_code", None)
    return code if isinstance(code, str) and code else type(program).__name__


def _dependencies_for(contributions: List[Contribution], slot: Slot) -> frozenset:
    """The dependency classes that contributed a value to one slot."""
    return frozenset(contribution.dependency for contribution in contributions if contribution.slot == slot)


def _describe_conflicts(
    contributions: List[Contribution],
    programs: List[PolicyEngineCalulator],
    grouped: List[List[int]],
    dropped: List[int],
) -> Tuple[List[str], List[str]]:
    """One line per disagreement, naming the slot, each value and who wanted it.

    Built here rather than at the log site because this is the only place that still knows
    which program produced which value. Returns every description, and separately the ones
    whose dependency classes are not a known pairing — those are a surprise worth raising,
    where a known pairing is just a second request (see EXPECTED_CONFLICTING_DEPENDENCIES).
    """
    if len(grouped) < 2 and not dropped:
        return [], []

    def labels(indexes) -> str:
        return ", ".join(sorted({_program_label(programs[index]) for index in indexes}))

    descriptions: List[str] = []
    unexpected: List[str] = []
    for slot, slot_groups in _group_by_value(contributions).items():
        if len(slot_groups) < 2:
            continue

        wanted = "; ".join(f"{value!r} ({labels(indexes)})" for value, indexes in slot_groups)
        description = f"{slot.field} at {slot.period} for {slot.unit}/{slot.sub_unit}: {wanted}"
        descriptions.append(description)

        if _dependencies_for(contributions, slot) not in EXPECTED_CONFLICTING_DEPENDENCIES:
            unexpected.append(description)

    return descriptions, unexpected
