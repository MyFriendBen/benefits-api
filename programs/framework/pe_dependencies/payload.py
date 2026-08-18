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

from typing import List, Optional

from screener.models import HouseholdMember, Screen

from programs.framework.pe_base import PolicyEngineCalulator
from programs.framework.pe_dependencies.base import DependencyError, Member, TaxUnit
from programs.framework.pe_dependencies.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT
from integrations.clients.policyengine import versions as pe_versions


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


def pe_input(
    screen: Screen,
    programs: List[PolicyEngineCalulator],
    pe_version: Optional[str] = None,
    resolved_version: Optional[tuple[str, Optional[tuple]]] = None,
):
    """
    Generate Policy Engine API request from the list of programs.

    `resolved_version` is the caller's already-resolved (version string, comparable version)
    pair, passed by `calc_pe_eligibility` so the version deciding which programs are readable
    is the one deciding which fields are sent. Direct callers may omit it.
    """
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

    members: list[HouseholdMember] = screen.household_members.all()
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

    for program in programs:
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

            period = program.pe_period
            if hasattr(program, "pe_output_period") and Data in program.pe_outputs:
                period = program.pe_output_period

            if issubclass(Data, Member):
                for member in members:
                    member_id = str(member.id)
                    data = Data(screen, member, relationship_map)
                    unit = raw_input["household"][data.unit][member_id]

                    update_unit(unit, data, period)
            elif issubclass(Data, TaxUnit):
                # split the household into the main and secondary tax unit.
                data = Data(screen, main_tax_members, relationship_map)
                unit = raw_input["household"][data.unit][MAIN_TAX_UNIT]

                update_unit(unit, data, period)

                data = Data(screen, secondary_tax_members, relationship_map)
                unit = raw_input["household"][data.unit][SECONDARY_TAX_UNIT]

                update_unit(unit, data, period)
            else:
                data = Data(screen, members, relationship_map)
                unit = raw_input["household"][data.unit][data.sub_unit]

                update_unit(unit, data, period)

    # delete the second tax unit if it is empty because PE can't handle empty tax units
    if len(secondary_tax_members) == 0:
        del raw_input["household"]["tax_units"][SECONDARY_TAX_UNIT]

    # Always inject the version (override > DB pin > "current"): determine_pe_version
    # never returns None, so a version is always sent.
    raw_input["version"] = version

    return raw_input


def update_unit(unit, data: PolicyEngineCalulator, period: str):
    value = data.value()
    if data.field in unit and period in unit[data.field]:
        if value != unit[data.field][period]:
            raise DependencyError(data.field, value, unit[data.field][period])

    if data.field not in unit:
        unit[data.field] = {}

    unit[data.field][period] = value
