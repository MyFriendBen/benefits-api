"""
PolicyEngineRequest - Builds PolicyEngine API requests.

This class handles the logic for forming a PolicyEngine API request from multiple
calculator configurations. One PE API call can serve multiple calculators/programs.
"""

from typing import List, Dict, Any, Type
from screener.models import Screen, HouseholdMember
from programs.programs.policyengine.calculators.dependencies.base import DependencyError
from programs.programs.policyengine.calculators.constants import MAIN_TAX_UNIT, SECONDARY_TAX_UNIT
from .inputs.base import PolicyEngineInput
from .outputs.base import PolicyEngineOutput


class PolicyEngineRequest:
    """
    Builds a PolicyEngine API request payload from multiple calculator configurations.

    This class encapsulates the logic for constructing the nested household structure
    that PolicyEngine expects, including people, tax units, families, households, and SPM units.

    A single PolicyEngineRequest can serve multiple calculators - all their inputs/outputs
    are merged into one API call.
    """

    def __init__(
        self,
        screen: Screen,
        configs: List
    ):
        """
        Initialize a PolicyEngineRequest.

        Args:
            screen: The Screen instance containing household data
            configs: List of Config instances (e.g., [TxSnapConfig(), CoMedicaidConfig()])
                    Each config has .pe_inputs, .pe_outputs, .period, and optionally .output_period
        """
        self.screen = screen
        self.configs = configs
        self.members: List[HouseholdMember] = list(screen.household_members.all())
        self.relationship_map = screen.relationship_map()

    def build(self) -> Dict[str, Any]:
        """
        Build the complete PolicyEngine API request payload.

        Returns:
            Dictionary representing the PolicyEngine API request structure
        """
        raw_input = self._initialize_structure()
        self._populate_members(raw_input)
        self._populate_marital_units(raw_input)
        self._populate_variables(raw_input)
        self._cleanup_empty_tax_units(raw_input)

        return raw_input

    def _initialize_structure(self) -> Dict[str, Any]:
        """Initialize the base PolicyEngine request structure."""
        return {
            "household": {
                "people": {},
                "tax_units": {
                    MAIN_TAX_UNIT: {"members": []},
                    SECONDARY_TAX_UNIT: {"members": []},
                },
                "families": {"family": {"members": []}},
                "households": {"household": {"members": []}},
                "spm_units": {"spm_unit": {"members": []}},
                "marital_units": {},
            }
        }

    def _populate_members(self, raw_input: Dict[str, Any]):
        """Populate member IDs across all household structures."""
        self.main_tax_members = []
        self.secondary_tax_members = []

        for member in self.members:
            member_id = str(member.id)
            household = raw_input["household"]

            # Add to all unit types
            household["families"]["family"]["members"].append(member_id)
            household["households"]["household"]["members"].append(member_id)
            household["spm_units"]["spm_unit"]["members"].append(member_id)
            household["people"][member_id] = {}

            # Add to appropriate tax unit
            if member.is_in_tax_unit():
                household["tax_units"][MAIN_TAX_UNIT]["members"].append(member_id)
                self.main_tax_members.append(member)
            else:
                household["tax_units"][SECONDARY_TAX_UNIT]["members"].append(member_id)
                self.secondary_tax_members.append(member)

    def _populate_marital_units(self, raw_input: Dict[str, Any]):
        """Populate marital units from relationship map."""
        already_added = set()

        for member_1, member_2 in self.relationship_map.items():
            if member_1 in already_added or member_2 in already_added or member_1 is None or member_2 is None:
                continue

            marital_unit = (str(member_1), str(member_2))
            raw_input["household"]["marital_units"]["-".join(marital_unit)] = {"members": marital_unit}
            already_added.add(member_1)
            already_added.add(member_2)

    def _populate_variables(self, raw_input: Dict[str, Any]):
        """Populate all input and output variables from all configs."""
        # Iterate through each config
        for config in self.configs:
            # Process inputs for this config
            for input_class in config.pe_inputs:
                period = config.period

                # Check unit type to determine how to instantiate
                if hasattr(input_class, 'unit') and input_class.unit == "people":
                    # Member-level input
                    self._populate_member_variable(raw_input, input_class, period)
                elif hasattr(input_class, 'unit') and input_class.unit == "tax_units":
                    # Tax unit input
                    self._populate_tax_unit_variable(raw_input, input_class, period)
                else:
                    # SPM/Household unit input
                    self._populate_unit_variable(raw_input, input_class, period)

            # Outputs don't add values to the request
            # PolicyEngine will calculate them based on the inputs provided

    def _populate_member_variable(self, raw_input: Dict[str, Any], input_class, period: str):
        """Populate a member-level variable."""
        for member in self.members:
            member_id = str(member.id)
            data_instance = input_class(self.screen, member, self.relationship_map)
            unit = raw_input["household"][data_instance.unit][member_id]
            self._update_unit(unit, data_instance, period)

    def _populate_tax_unit_variable(self, raw_input: Dict[str, Any], input_class, period: str):
        """Populate a tax-unit-level variable (split into main and secondary)."""
        # Main tax unit
        data_instance = input_class(self.screen, self.main_tax_members, self.relationship_map)
        unit = raw_input["household"][data_instance.unit][MAIN_TAX_UNIT]
        self._update_unit(unit, data_instance, period)

        # Secondary tax unit
        data_instance = input_class(self.screen, self.secondary_tax_members, self.relationship_map)
        unit = raw_input["household"][data_instance.unit][SECONDARY_TAX_UNIT]
        self._update_unit(unit, data_instance, period)

    def _populate_unit_variable(self, raw_input: Dict[str, Any], input_class, period: str):
        """Populate a household/SPM-unit-level variable."""
        data_instance = input_class(self.screen, self.members, self.relationship_map)
        unit = raw_input["household"][data_instance.unit][data_instance.sub_unit]
        self._update_unit(unit, data_instance, period)

    def _update_unit(self, unit: Dict[str, Any], data_instance, period: str):
        """
        Update a unit with a variable value, checking for conflicts.

        Args:
            unit: The unit dictionary to update
            data_instance: The dependency instance to get the value from
            period: The time period for this variable

        Raises:
            DependencyError: If there's a conflicting value for the same field/period
        """
        value = data_instance.value()

        # Check for conflicts
        if data_instance.field in unit and period in unit[data_instance.field]:
            if value != unit[data_instance.field][period]:
                raise DependencyError(data_instance.field, value, unit[data_instance.field][period])

        # Set the value
        if data_instance.field not in unit:
            unit[data_instance.field] = {}

        unit[data_instance.field][period] = value

    def _cleanup_empty_tax_units(self, raw_input: Dict[str, Any]):
        """Remove secondary tax unit if empty (PolicyEngine can't handle empty tax units)."""
        if len(self.secondary_tax_members) == 0:
            del raw_input["household"]["tax_units"][SECONDARY_TAX_UNIT]
