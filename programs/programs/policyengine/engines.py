from typing import Optional
from integrations.util.cache import Cache
from decouple import config
import requests


class PolicyEngineAPIError(RuntimeError):
    """A PolicyEngine request failed. Carries the HTTP status code (when the failure
    was an HTTP error response) for diagnostics. There is no fallback endpoint: a
    failure means PolicyEngine programs are unavailable for the screen, so it is
    surfaced loudly and reported to the frontend rather than silently worked around."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _request_failed_message(method_name: str, error: Exception) -> str:
    """Build the failure message, including PolicyEngine's response body when present.
    raise_for_status() omits the body, but that's where PE explains *why* (e.g. an
    unknown version or variable) — surface it so the error is diagnosable in Sentry."""
    body = ""
    response = getattr(error, "response", None)
    if response is not None:
        body = f" — {response.text}"
    return f"{method_name} request failed {error}{body}"


class Sim:
    method_name = ""

    def __init__(self, data) -> None:
        self.data = data

    def value(self, unit, sub_unit, variable, period):
        """
        Calculate variable at the period
        """
        raise NotImplementedError

    def members(self, unit, sub_unit):
        """
        Return a list of the members in the sub unit
        """
        raise NotImplementedError


class PolicyEngineBearerTokenCache(Cache):
    expire_time = 60 * 60 * 24 * 29
    default = ""
    client_id: str = config("POLICY_ENGINE_CLIENT_ID", "")
    client_secret: str = config("POLICY_ENGINE_CLIENT_SECRET", "")
    domain = "https://policyengine.uk.auth0.com"
    endpoint = "/oauth/token"

    def update(self):
        # https://policyengine.org/us/api#fetch_token

        if self.client_id == "" or self.client_secret == "":
            raise Exception("client id or secret not configured")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "audience": "https://household.api.policyengine.org",
        }

        res = requests.post(self.domain + self.endpoint, json=payload, timeout=(5, 30))

        return res.json()["access_token"]


class PrivateApiSim(Sim):
    """The only PolicyEngine engine: the authenticated private household.api endpoint.

    We do NOT fall back to the public api.policyengine.org: it ignores the request
    `version` field (verified against its source — the /calculate handler reads only
    household+policy and has no version parameter), so it can silently compute against
    a different model version than the one we resolve and pin here. If this request
    fails, PolicyEngine programs are treated as unavailable for the screen (see
    calc_pe_eligibility)."""

    method_name = "Private Policy Engine API"
    token = PolicyEngineBearerTokenCache()
    pe_url = "https://household.api.policyengine.org/us/calculate"

    def __init__(self, data) -> None:
        token = self.token.fetch()

        headers = {
            "Authorization": f"Bearer {token}",
        }

        self.request_payload = data
        try:
            res = requests.post(self.pe_url, json=data, headers=headers, timeout=(5, 30))
            res.raise_for_status()
            self.response_json = res.json()
        except requests.RequestException as e:
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            raise PolicyEngineAPIError(_request_failed_message(self.method_name, e), status_code) from e
        except ValueError as e:
            raise PolicyEngineAPIError(f"{self.method_name} returned non-JSON {e}") from e
        if "result" not in self.response_json:
            raise PolicyEngineAPIError("Missing 'result' key in Policy Engine response")
        self.data = self.response_json["result"]

    def value(self, unit, sub_unit, variable, period):
        return self.data[unit][sub_unit][variable][period]

    def members(self, unit, sub_unit):
        return self.data[unit][sub_unit]["members"]


pe_engines: list[Sim] = [PrivateApiSim]
