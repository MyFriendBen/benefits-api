"""
Duration calculation service for SNAP lifetime benefit value estimation.
Implements simple multiplier-based duration calculation based on research data.
"""

from typing import Dict, Any
from programs.models import Program, ProgramDurationMultiplier
from screener.models import WhiteLabel


class SimpleDurationService:
    """
    Basic multiplier-based duration estimation service.
    Uses research-based duration averages stored in ProgramDurationMultiplier model.
    """

    def calculate_duration(self, program: Program, white_label: WhiteLabel) -> Dict[str, Any]:
        """
        Calculate duration for a program using simple multiplier approach.

        Args:
            program: The benefit program
            white_label: The white label (state/organization) context

        Returns:
            Dictionary containing:
            - average_duration_months: Average duration in months
            - confidence_range: Tuple of (lower_bound, upper_bound) in months
            - data_source: Source of the duration data

        Raises:
            ProgramDurationMultiplier.DoesNotExist: If no multiplier exists for the program/white_label
        """
        try:
            multiplier = ProgramDurationMultiplier.objects.get(program=program, white_label=white_label)
        except ProgramDurationMultiplier.DoesNotExist:
            raise ValueError(
                f"No duration multiplier found for program {program.name_abbreviated} "
                f"in white label {white_label.code}"
            )

        # Calculate confidence range using multipliers
        average_duration = multiplier.average_duration_months
        lower_bound = average_duration * multiplier.confidence_range_lower
        upper_bound = average_duration * multiplier.confidence_range_upper

        return {
            "average_duration_months": average_duration,
            "confidence_range": (lower_bound, upper_bound),
            "data_source": multiplier.data_source,
        }

    def get_available_programs(self, white_label: WhiteLabel) -> list[Program]:
        """
        Get list of programs that have duration multipliers configured for the white label.

        Args:
            white_label: The white label to check

        Returns:
            List of Program objects that have duration data available
        """
        multipliers = ProgramDurationMultiplier.objects.filter(white_label=white_label)
        return [multiplier.program for multiplier in multipliers]

    def validate_duration_data(self, program: Program, white_label: WhiteLabel) -> bool:
        """
        Validate that duration data exists and is reasonable for the given program/white_label.

        Args:
            program: The benefit program
            white_label: The white label context

        Returns:
            True if duration data exists and passes basic validation
        """
        try:
            duration_data = self.calculate_duration(program, white_label)

            # Basic validation checks
            avg_duration = duration_data["average_duration_months"]
            confidence_range = duration_data["confidence_range"]

            # Duration should be positive and reasonable (1 month to 10 years)
            if not (1 <= avg_duration <= 120):
                return False

            # Confidence range should be valid
            if confidence_range[0] >= confidence_range[1]:
                return False

            # Lower bound should be positive
            if confidence_range[0] <= 0:
                return False

            return True

        except (ValueError, KeyError):
            return False
