from django.core.cache import cache
from decouple import config
import requests


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


class ApiSim(Sim):
    method_name = "Policy Engine API"
    pe_url = "https://api.policyengine.org/us/calculate"

    def __init__(self, data) -> None:
        self.request_payload = data
        try:
            res = requests.post(self.pe_url, json=data, timeout=(5, 30))
            res.raise_for_status()
            self.response_json = res.json()
        except requests.RequestException as e:
            raise RuntimeError(f"{self.method_name} request failed {e}") from e
        except ValueError as e:
            raise RuntimeError(f"{self.method_name} returned non-JSON {e}") from e
        if "result" not in self.response_json:
            raise RuntimeError("Missing 'result' key in Policy Engine response")
        self.data = self.response_json["result"]

    def value(self, unit, sub_unit, variable, period):
        return self.data[unit][sub_unit][variable][period]

    def members(self, unit, sub_unit):
        return self.data[unit][sub_unit]["members"]


_PE_TOKEN_CACHE_KEY = "pe_bearer_token"
_PE_TOKEN_TIMEOUT = 60 * 60 * 24 * 29  # 29 days

_pe_client_id: str = config("POLICY_ENGINE_CLIENT_ID", "")
_pe_client_secret: str = config("POLICY_ENGINE_CLIENT_SECRET", "")
_pe_token_url = "https://policyengine.uk.auth0.com/oauth/token"


def _fetch_pe_bearer_token() -> str:
    token = cache.get(_PE_TOKEN_CACHE_KEY)
    if token is not None:
        return token

    if not _pe_client_id or not _pe_client_secret:
        raise Exception("Policy Engine client id or secret not configured")

    payload = {
        "client_id": _pe_client_id,
        "client_secret": _pe_client_secret,
        "grant_type": "client_credentials",
        "audience": "https://household.api.policyengine.org",
    }
    try:
        res = requests.post(_pe_token_url, json=payload, timeout=(5, 30))
        res.raise_for_status()
        token = res.json()["access_token"]
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch PolicyEngine bearer token: {e}") from e

    cache.set(_PE_TOKEN_CACHE_KEY, token, timeout=_PE_TOKEN_TIMEOUT)
    return token


class PrivateApiSim(ApiSim):
    method_name = "Private Policy Engine API"
    pe_url = "https://household.api.policyengine.org/us/calculate"

    def __init__(self, data) -> None:
        token = _fetch_pe_bearer_token()

        headers = {
            "Authorization": f"Bearer {token}",
        }

        self.request_payload = data
        try:
            res = requests.post(self.pe_url, json=data, headers=headers, timeout=(5, 30))
            res.raise_for_status()
            self.response_json = res.json()
        except requests.RequestException as e:
            raise RuntimeError(f"{self.method_name} request failed {e}") from e
        except ValueError as e:
            raise RuntimeError(f"{self.method_name} returned non-JSON {e}") from e
        if "result" not in self.response_json:
            raise RuntimeError("Missing 'result' key in Policy Engine response")
        self.data = self.response_json["result"]


pe_engines: list[Sim] = [PrivateApiSim, ApiSim]
