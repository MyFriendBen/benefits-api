from integrations.util.cache import Cache
from decouple import config
import requests
import json
import logging

# Set up logger for PolicyEngine API debugging
logger = logging.getLogger('policyengine_api')
logger.setLevel(logging.DEBUG)

# Create console handler if not exists
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


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
        logger.info("=" * 80)
        logger.info(f"PolicyEngine API Request to {self.pe_url}")
        logger.info("Request data:")
        logger.info(json.dumps(data, indent=2))
        
        response = requests.post(self.pe_url, json=data)
        
        logger.info(f"Response status: {response.status_code}")
        response_data = response.json()
        logger.info("Response data:")
        logger.info(json.dumps(response_data, indent=2))
        
        self.data = response_data["result"]
        
        # Log specific ACA PTC values if present
        if "tax_units" in self.data:
            for tax_unit_id, tax_unit_data in self.data["tax_units"].items():
                if "aca_ptc" in tax_unit_data:
                    logger.info(f"ACA PTC for {tax_unit_id}: {tax_unit_data['aca_ptc']}")
        logger.info("=" * 80)

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
        logger.info("=" * 80)
        logger.info(f"Private PolicyEngine API Request to {self.pe_url}")
        logger.info("Request data:")
        logger.info(json.dumps(data, indent=2))
        
        token = self.token.fetch()

        headers = {
            "Authorization": f"Bearer {token}",
        }

        res = requests.post(self.pe_url, json=data, headers=headers)
        
        logger.info(f"Response status: {res.status_code}")
        response_data = res.json()
        logger.info("Response data:")
        logger.info(json.dumps(response_data, indent=2))
        
        self.data = response_data["result"]
        
        # Log specific ACA PTC values if present
        if "tax_units" in self.data:
            for tax_unit_id, tax_unit_data in self.data["tax_units"].items():
                if "aca_ptc" in tax_unit_data:
                    logger.info(f"ACA PTC for {tax_unit_id}: {tax_unit_data['aca_ptc']}")
        logger.info("=" * 80)


pe_engines: list[Sim] = [PrivateApiSim, ApiSim]
