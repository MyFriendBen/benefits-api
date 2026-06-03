from screener.models import HouseholdMember, Screen
from .calculators import PolicyEngineCalulator
from programs.programs.calc import Eligibility
from .calculators.dependencies.base import DependencyError, Member, TaxUnit
from typing import Any, Dict, List, Optional, TypedDict
from sentry_sdk import capture_exception, capture_message
from .engines import Sim, pe_engines
from .calculators.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT
from django.conf import settings


class PEData(TypedDict):
    request: Optional[Dict[str, Any]]
    response: Optional[Dict[str, Any]]


class EligibilityPEResult(TypedDict):
    eligibility: Dict[str, Eligibility]
    _pe_data: PEData


def resolve_pe_version(pe_version_override: Optional[str] = None) -> Optional[str]:
    """
    Resolve the PolicyEngine model version to send: per-request override (test-only,
    passed down from the view) wins, then the global PolicyEngineConfig pin, else None
    (omit the field, i.e. PolicyEngine's default). The override may be a floating alias
    ("frontier"/"current"); the config value may not (enforced on the model).
    """
    if pe_version_override:
        return pe_version_override

    # Deferred to keep this calculator module's import graph light (it avoids pulling
    # the configuration model layer at import time); there is no import cycle.
    from configuration.models import PolicyEngineConfig

    # Read-only accessor: must not write a row on the eligibility hot path.
    return PolicyEngineConfig.current_version() or None


# Sentinel meaning "newest released model" — supports any gated variable.
_LATEST = (float("inf"),)


def _parse_version(version: Optional[str]) -> Optional[tuple]:
    """
    Turn a resolved version into a comparable tuple for input gating:
      - "1.715.2"  -> (1, 715, 2)
      - "frontier" -> _LATEST (newest released model, supports gated inputs)
      - "current" / None / unparseable -> None (treat as the current default model)
    """
    if version == "frontier":
        return _LATEST
    if not version or version == "current":
        return None
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None


def _version_supports(parsed_version: Optional[tuple], min_pe_version: tuple, max_pe_version: tuple) -> bool:
    """Whether a request at parsed_version may send an input that exists in the version
    window [min_pe_version, max_pe_version] (each bound optional). Ungated inputs (both
    empty) are always sent.

    parsed_version is None for an unknown/current/unpinned request. We treat that
    asymmetrically: it FAILS any min floor (don't send a not-yet-existing variable to
    the current model) but SATISFIES any max ceiling (a variable that still exists on
    the current model should keep being sent until we pin a version past its removal)."""
    if min_pe_version:
        if parsed_version is None or parsed_version < min_pe_version:
            return False
    if max_pe_version:
        if parsed_version is not None and parsed_version > max_pe_version:
            return False
    return True


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
    # Resolve once: used both to gate version-specific inputs below and to set the
    # top-level "version" field. None => no pin (PolicyEngine's current default).
    version = resolve_pe_version(pe_version)
    parsed_version = _parse_version(version)

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
            # on 1.691.1). With no pin (parsed_version is None) we omit gated inputs too,
            # since the unpinned default is the current model that lacks them.
            if not _version_supports(
                parsed_version,
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
