from screener.models import Screen
from programs.framework.pe_base import PolicyEngineCalulator
from programs.framework.base import Eligibility
from typing import Any, Dict, Optional, TypedDict
from sentry_sdk import capture_exception, capture_message
from .engines import Sim, pe_engines
from programs.framework.pe_dependencies.payload import _resolve_comparable_version, pe_input
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
