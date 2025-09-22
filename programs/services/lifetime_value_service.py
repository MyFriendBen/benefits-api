"""
Lifetime value service for SNAP benefit estimation.
Orchestrates lifetime benefit value calculation using simple multiplier approach.
"""

from decimal import Decimal
from typing import Optional
from programs.models import Program, LifetimeValuePrediction
from programs.services.duration_calculation_service import SimpleDurationService
from screener.models import Screen


class LifetimeValueService:
    """
    Main orchestration service for SNAP lifetime benefit value calculation.
    Uses SimpleDurationService for duration estimation and generates AI explanations.
    """

    def __init__(self):
        self.duration_service = SimpleDurationService()

    def generate_prediction(
        self, screen: Screen, program: Program, monthly_benefit: Decimal
    ) -> LifetimeValuePrediction:
        """
        Generate a complete SNAP lifetime benefit value prediction.

        Args:
            screen: The household screen data
            program: The SNAP program
            monthly_benefit: The monthly benefit amount for the household

        Returns:
            LifetimeValuePrediction instance with calculated values and explanations

        Raises:
            ValueError: If no duration data exists for the program/white_label combination
        """
        # Get duration data using SimpleDurationService
        duration_data = self.duration_service.calculate_duration(program, screen.white_label)

        # Calculate lifetime value
        predicted_duration = duration_data["average_duration_months"]
        confidence_range = duration_data["confidence_range"]
        estimated_lifetime_value = monthly_benefit * Decimal(str(predicted_duration))

        # Generate basic explanation (placeholder for AI service integration)
        explanation_text = self._generate_basic_explanation(
            program=program,
            duration_months=predicted_duration,
            monthly_benefit=monthly_benefit,
            estimated_lifetime_value=estimated_lifetime_value,
            data_source=duration_data["data_source"],
        )

        # Generate risk assessment
        risk_assessment = self._generate_basic_risk_assessment(confidence_range)

        # Create and save prediction
        prediction = LifetimeValuePrediction.objects.create(
            screen=screen,
            program=program,
            predicted_duration_months=predicted_duration,
            confidence_interval_lower=confidence_range[0],
            confidence_interval_upper=confidence_range[1],
            estimated_lifetime_value=estimated_lifetime_value,
            explanation_text=explanation_text,
            risk_assessment=risk_assessment,
            multiplier_version="1.0",
            calculation_method="simple_multiplier",
        )

        return prediction

    def _generate_basic_explanation(
        self,
        program: Program,
        duration_months: float,
        monthly_benefit: Decimal,
        estimated_lifetime_value: Decimal,
        data_source: str,
    ) -> str:
        """
        Generate a basic user-friendly explanation for the lifetime projection.
        This is a placeholder that will be enhanced with AI service integration.
        """
        program_name = "SNAP" if "snap" in program.name_abbreviated.lower() else program.name_abbreviated

        explanation = (
            f"Based on research data from {data_source}, families similar to yours typically "
            f"receive {program_name} benefits for about {duration_months:.0f} months. "
            f"With your monthly benefit of ${monthly_benefit}, this could provide "
            f"approximately ${estimated_lifetime_value:,.2f} in total food assistance over time. "
            f"This estimate helps you understand the potential long-term value of this benefit program."
        )

        return explanation

    def _generate_basic_risk_assessment(self, confidence_range: tuple[float, float]) -> str:
        """
        Generate a basic risk assessment based on confidence range.
        This is a placeholder that will be enhanced with AI service integration.
        """
        lower_months = confidence_range[0]
        upper_months = confidence_range[1]

        risk_assessment = (
            f"The actual duration you receive benefits may vary between "
            f"{lower_months:.0f} and {upper_months:.0f} months, depending on your specific circumstances "
            f"such as changes in income, household size, or work status. "
            f"This estimate is based on general patterns and your individual experience may differ."
        )

        return risk_assessment

    def get_cached_prediction(self, screen: Screen, program: Program) -> Optional[LifetimeValuePrediction]:
        """
        Get most recent cached prediction for a screen/program combination.

        Args:
            screen: The household screen
            program: The benefit program

        Returns:
            Most recent LifetimeValuePrediction or None if no cached prediction exists
        """
        try:
            return (
                LifetimeValuePrediction.objects.filter(screen=screen, program=program)
                .order_by("-prediction_date")
                .first()
            )
        except LifetimeValuePrediction.DoesNotExist:
            return None

    def validate_prediction_inputs(self, screen: Screen, program: Program, monthly_benefit: Decimal) -> bool:
        """
        Validate that inputs for prediction generation are valid.

        Args:
            screen: The household screen
            program: The benefit program
            monthly_benefit: The monthly benefit amount

        Returns:
            True if inputs are valid for prediction generation
        """
        # Check that duration data exists
        if not self.duration_service.validate_duration_data(program, screen.white_label):
            return False

        # Check that monthly benefit is positive
        if monthly_benefit <= 0:
            return False

        # Check that screen has required data
        if not screen.household_size or screen.household_size <= 0:
            return False

        return True
