import json
from integrations.util.cache import Cache
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

        res = requests.post(self.domain + self.endpoint, json=payload)

        return res.json()["access_token"]


class PrivateApiSim(ApiSim):
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
            raise RuntimeError(f"{self.method_name} request failed {e}") from e
        except ValueError as e:
            raise RuntimeError(f"{self.method_name} returned non-JSON {e}") from e
        if "result" not in self.response_json:
            raise RuntimeError("Missing 'result' key in Policy Engine response")
        self.data = self.response_json["result"]


pe_engines: list[Sim] = [PrivateApiSim, ApiSim]
