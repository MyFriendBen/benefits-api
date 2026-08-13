from screener.models import HouseholdMember, Screen
from .calculators import PolicyEngineCalulator
from programs.programs.calc import Eligibility
from .calculators.dependencies.base import DependencyError, Member, TaxUnit
from typing import Any, Dict, List, Optional, TypedDict
from sentry_sdk import capture_exception, capture_message
from .engines import Sim, pe_engines
from .calculators.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT
from . import versions as pe_versions
from integrations.external_api_status import record_external_api_failure, POLICY_ENGINE
from django.conf import settings


class PEData(TypedDict):
    request: Optional[Dict[str, Any]]
    response: Optional[Dict[str, Any]]


class EligibilityPEResult(TypedDict):
    eligibility: Dict[str, Eligibility]
    _pe_data: PEData


def calc_pe_eligibility(
    screen: Screen,
    calculators: dict[str, PolicyEngineCalulator],
    pe_version: Optional[str] = None,
) -> EligibilityPEResult:
    valid_programs: dict[str, PolicyEngineCalulator] = {}

    for name_abbr, calculator in calculators.items():
        if not calculator.can_calc():
            continue
        valid_programs[name_abbr] = calculator

    # Resolve the model version ONCE and thread it through both consumers: independent
    # resolutions can disagree (PolicyEngine promotes a new `current`, or our cached lookup
    # expires or fails between calls), and a disagreement is exactly the failure
    # _drop_unreadable_programs exists to prevent — a program kept because the first
    # resolution supported its output, then its field withheld because the second didn't.
    version = pe_versions.determine_pe_version(pe_version)
    comparable_version = _resolve_comparable_version(list(valid_programs.values()), version)

    valid_programs = _drop_unreadable_programs(valid_programs, comparable_version)

    empty_result: EligibilityPEResult = {
        "eligibility": {},
        "_pe_data": {"request": None, "response": None},
    }

    if not valid_programs or not screen.household_members.all():
        return empty_result

    input_data = pe_input(
        screen,
        valid_programs.values(),
        pe_version=pe_version,
        resolved_version=(version, comparable_version),
    )

    # A single engine: the authenticated private household.api. There is deliberately no
    # fallback to the public api.policyengine.org — it ignores the request `version` field
    # (verified against its source) and would silently compute against a different model
    # version than the one we resolve and pin. So any failure here means PolicyEngine
    # programs are unavailable for this screen.
    for Method in pe_engines:
        try:
            method_instance = Method(input_data)
            eligibility = all_eligibility(method_instance, valid_programs)
            result: EligibilityPEResult = {
                "eligibility": eligibility,
                "_pe_data": {
                    "request": getattr(method_instance, "request_payload", None),
                    "response": getattr(method_instance, "response_json", None),
                },
            }
        except (SystemExit, KeyboardInterrupt) as e:
            # Worker is being torn down: gunicorn's SIGABRT handler (fired when a request
            # exceeds the worker --timeout, e.g. while a PE HTTP call hangs on DNS) calls
            # sys.exit(), raising SystemExit. That is a BaseException, so the `except
            # Exception` below never sees it and the death is invisible in Sentry. Capture
            # it here for visibility, then re-raise so the shutdown proceeds normally.
            capture_exception(e, level="error")
            capture_message(
                f"Worker exited mid-request while calculating eligibility with the " f"{Method.method_name} method",
                level="error",
            )
            raise
        except Exception as e:
            # Any PolicyEngine failure (malformed payload/400, timeout, 5xx, auth, non-JSON):
            # with no fallback endpoint, PolicyEngine programs can't be computed for this
            # screen. Surface it loudly (Sentry error), record it so the frontend can warn
            # the user, and return an empty PE result so the caller still computes the
            # non-PolicyEngine (custom) calculators.
            if settings.DEBUG:
                print(repr(e))
            capture_exception(e, level="error")
            capture_message(
                f"Failed to calculate eligibility with the {Method.method_name} method; "
                f"PolicyEngine programs are unavailable for this screen.",
                level="error",
            )
            record_external_api_failure(POLICY_ENGINE)
            # Preserve the payload that triggered the failure so admins can debug it
            # (the exact request is the most useful thing for diagnosing a 400).
            # _pe_data.request is admin-only — already popped for non-admins downstream.
            return {
                "eligibility": {},
                "_pe_data": {"request": input_data, "response": None},
            }
        else:
            return result

    return empty_result


def all_eligibility(method: Sim, valid_programs: dict[str, PolicyEngineCalulator]):
    all_eligibility: dict[str, Eligibility] = {}
    for name_abbr, calculator in valid_programs.items():
        calculator.set_engine(method)

        e = calculator.calc()

        all_eligibility[name_abbr] = e

    return all_eligibility


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


def _drop_unreadable_programs(
    valid_programs: dict[str, PolicyEngineCalulator],
    comparable_version: Optional[tuple],
) -> dict[str, PolicyEngineCalulator]:
    """Drop programs whose own output variable the resolved model doesn't define.

    Version gating withholds such a field, so PolicyEngine never returns it and `Sim.value`
    raises KeyError on the missing key. `all_eligibility` has no per-program error handling, so
    one unreadable program would empty the PE result for the whole screen.

    Gated *inputs* need no equivalent — withholding one just leaves PolicyEngine to model the
    value itself. Only outputs are load-bearing this way, and the receipt-contract outputs are
    the first gated ones in the codebase.

    Reachable via an exact `PolicyEngineConfig` pin below a floor, or via /versions/us being
    unreachable while /calculate is healthy. `comparable_version` is the request's single
    resolved version; None conservatively drops every program carrying a gated output.
    """
    if not valid_programs:
        return valid_programs

    readable: dict[str, PolicyEngineCalulator] = {}
    dropped: list[str] = []
    for name_abbr, calculator in valid_programs.items():
        unsupported = [
            Data.field
            for Data in calculator.pe_outputs
            if not pe_versions.version_supports(
                comparable_version,
                getattr(Data, "min_pe_version", ()),
                getattr(Data, "max_pe_version", ()),
            )
        ]
        if unsupported:
            dropped.append(f"{name_abbr} ({', '.join(unsupported)})")
            continue
        readable[name_abbr] = calculator

    if dropped:
        # Make the reason visible rather than leaving it inferred from a program's absence.
        capture_message(
            f"PolicyEngine: dropped {len(dropped)} program(s) whose output variable the resolved "
            f"model version does not define: {sorted(dropped)}",
            level="warning",
        )

    return readable


def _has_gated_input(programs: List[PolicyEngineCalulator]) -> bool:
    """True if any input/output in these programs is version-gated (has a
    min_pe_version or max_pe_version). Lets us skip resolving the PE version when
    nothing in the request depends on it."""
    for program in programs:
        for Data in program.pe_inputs + program.pe_outputs:
            if getattr(Data, "min_pe_version", ()) or getattr(Data, "max_pe_version", ()):
                return True
    return False


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
