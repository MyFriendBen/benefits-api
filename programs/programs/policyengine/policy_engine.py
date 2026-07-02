from screener.models import HouseholdMember, Screen
from .calculators import PolicyEngineCalulator
from programs.programs.calc import Eligibility
from .calculators.dependencies.base import DependencyError, Member, TaxUnit
from typing import Any, Dict, List, Optional, TypedDict
from sentry_sdk import capture_exception, capture_message
from .engines import Sim, pe_engines
from .calculators.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT
from . import versions as pe_versions
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

    empty_result: EligibilityPEResult = {
        "eligibility": {},
        "_pe_data": {"request": None, "response": None},
    }

    if not valid_programs or not screen.household_members.all():
        return empty_result

    input_data = pe_input(screen, valid_programs.values(), pe_version=pe_version)

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
            if settings.DEBUG:
                print(repr(e))
            capture_exception(e, level="warning")
            capture_message(
                f"Failed to calculate eligibility with the {Method.method_name} method",
                level="warning",
            )
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


def _has_gated_input(programs: List[PolicyEngineCalulator]) -> bool:
    """True if any input/output in these programs is version-gated (has a
    min_pe_version or max_pe_version). Lets us skip resolving the PE version when
    nothing in the request depends on it."""
    for program in programs:
        for Data in program.pe_inputs + program.pe_outputs:
            if getattr(Data, "min_pe_version", ()) or getattr(Data, "max_pe_version", ()):
                return True
    return False


def pe_input(screen: Screen, programs: List[PolicyEngineCalulator], pe_version: Optional[str] = None):
    """
    Generate Policy Engine API request from the list of programs.
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
    #   version (string)            -> version to send in PE API request body (if None/omitted,
    #                                   PE defaults to current version)
    #   comparable_version (tuple)  -> tuple representation to gate which inputs are sent
    version = pe_versions.determine_pe_version(pe_version)
    comparable_version = pe_versions.to_comparable_pe_version(version)

    # No pin (and no exact override) means "ride PE's current model": we omit the
    # version string so PE serves current, but for input gating we still need to know
    # what current concretely is — otherwise a min_pe_version floor can never be met
    # and gated inputs (e.g. use_reported_ssi) are withheld forever. Resolve current
    # from PE's published /versions/us. If PE is unreachable this stays None, keeping
    # the conservative withhold-gated behavior (safe: PE just uses modeled values).
    #
    # Only bother resolving when this request actually carries a version-gated input —
    # the vast majority don't, and resolving would be a needless (cached) lookup.
    if comparable_version is None and _has_gated_input(programs):
        comparable_version = pe_versions.resolve_unpinned_comparable_version()

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
            # Skip inputs that the resolved model version doesn't define yet — sending
            # an unknown variable 400s the whole request (e.g. meets_ssi_disability_criteria
            # on 1.691.1). With no pin (comparable_version is None) we omit gated inputs
            # too, since the unpinned default is the current model that lacks them.
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

    # Inject the resolved version (override > config); None means omit the field.
    if version is not None:
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
