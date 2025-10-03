"""
Lifetime value service for SNAP benefit estimation.
Orchestrates lifetime benefit value calculation using simple multiplier approach.
"""

import logging
from decimal import Decimal
from typing import Optional
from django.conf import settings

from programs.models import Program, LifetimeValuePrediction
from programs.services.duration_calculation_service import SimpleDurationService
from programs.services.ai_communication_service import AICommunicationService
from screener.models import Screen


logger = logging.getLogger(__name__)


class LifetimeValueService:
    """
    Main orchestration service for SNAP lifetime benefit value calculation.
    Uses SimpleDurationService for duration estimation and generates AI explanations.
    """

    def __init__(self):
        self.duration_service = SimpleDurationService()
        self.ai_service = None

        # Initialize AI service if enabled and configured
        if getattr(settings, "AI_EXPLANATION_ENABLED", True):
            try:
                self.ai_service = AICommunicationService()
                logger.info("AI communication service initialized successfully")
                print("✅ AI communication service initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize AI service: {e}. Falling back to basic explanations.")
                print(f"❌ Failed to initialize AI service: {e}. Falling back to basic explanations.")

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

        # Generate explanations using AI service or fallback to basic
        explanations = self._generate_explanations(
            screen=screen,
            program=program,
            duration_data=duration_data,
            monthly_benefit=monthly_benefit,
            estimated_lifetime_value=estimated_lifetime_value,
        )

        explanation_text = explanations["explanation"]
        risk_assessment = explanations["risk_assessment"]

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

    def _generate_explanations(
        self,
        screen: Screen,
        program: Program,
        duration_data: dict,
        monthly_benefit: Decimal,
        estimated_lifetime_value: Decimal,
    ) -> dict:
        """
        Generate explanations using AI service or fallback to basic explanations.

        Args:
            screen: The household screen data
            program: The benefit program
            duration_data: Duration calculation data
            monthly_benefit: Monthly benefit amount
            estimated_lifetime_value: Calculated lifetime value

        Returns:
            Dictionary with 'explanation' and 'risk_assessment' keys
        """
        # Prepare lifetime data for AI service
        lifetime_data = {
            "predicted_duration_months": duration_data["average_duration_months"],
            "confidence_interval_lower": duration_data["confidence_range"][0],
            "confidence_interval_upper": duration_data["confidence_range"][1],
            "estimated_lifetime_value": estimated_lifetime_value,
            "monthly_benefit": monthly_benefit,
            "data_source": duration_data["data_source"],
        }

        # Try AI service first if available
        if self.ai_service:
            try:
                logger.info("✨ Generating explanations using AI service")
                print("🤖 AI SERVICE: Generating explanations using AI service")
                ai_response = self.ai_service.generate_explanation(lifetime_data, screen, program)
                print("📄 AI RESPONSE:")
                print(f"  Explanation: {ai_response.get('explanation', 'N/A')[:200]}...")
                print(f"  Risk Assessment: {ai_response.get('risk_assessment', 'N/A')[:200]}...")
                return ai_response
            except Exception as e:
                logger.warning(f"AI service failed, falling back to basic explanations: {e}")

        # Fallback to basic explanations
        logger.info("📝 Using basic explanation generation (AI service not available)")
        print("📝 FALLBACK: Using basic explanation generation (AI service not available)")
        explanation_text = self._generate_basic_explanation(
            program=program,
            duration_months=duration_data["average_duration_months"],
            monthly_benefit=monthly_benefit,
            estimated_lifetime_value=estimated_lifetime_value,
            data_source=duration_data["data_source"],
            language_code=screen.get_language_code(),
        )

        risk_assessment = self._generate_basic_risk_assessment(
            confidence_range=duration_data["confidence_range"],
            language_code=screen.get_language_code(),
        )

        basic_response = {"explanation": explanation_text, "risk_assessment": risk_assessment}
        print("📄 BASIC RESPONSE:")
        print(f"  Explanation: {explanation_text[:200]}...")
        print(f"  Risk Assessment: {risk_assessment[:200]}...")
        return basic_response

    def _generate_basic_explanation(
        self,
        program: Program,
        duration_months: float,
        monthly_benefit: Decimal,
        estimated_lifetime_value: Decimal,
        data_source: str,
        language_code: str = "en-us",
    ) -> str:
        """
        Generate a basic user-friendly explanation for the lifetime projection.
        Fallback method when AI service is unavailable.

        Args:
            program: The benefit program
            duration_months: Predicted duration in months
            monthly_benefit: Monthly benefit amount
            estimated_lifetime_value: Total estimated value
            data_source: Source of the duration data
            language_code: Language code for localization

        Returns:
            Basic explanation text
        """
        program_name = "SNAP" if "snap" in program.name_abbreviated.lower() else program.name_abbreviated

        if language_code.startswith("es"):
            explanation = (
                f"Basado en datos de investigación de {data_source}, las familias como la suya "
                f"típicamente reciben beneficios de {program_name} durante aproximadamente "
                f"{duration_months:.0f} meses. Con su beneficio mensual de ${monthly_benefit}, "
                f"esto podría proporcionar aproximadamente ${estimated_lifetime_value:,.2f} "
                f"en asistencia alimentaria total a lo largo del tiempo. Esta estimación le ayuda a "
                f"entender el valor potencial a largo plazo de este programa de beneficios."
            )
        else:
            explanation = (
                f"Based on research data from {data_source}, families similar to yours typically "
                f"receive {program_name} benefits for about {duration_months:.0f} months. "
                f"With your monthly benefit of ${monthly_benefit}, this could provide "
                f"approximately ${estimated_lifetime_value:,.2f} in total food assistance over time. "
                f"This estimate helps you understand the potential long-term value of this benefit program."
            )

        return explanation

    def _generate_basic_risk_assessment(
        self,
        confidence_range: tuple[float, float],
        language_code: str = "en",
    ) -> str:
        """
        Generate a basic risk assessment based on confidence range.
        Fallback method when AI service is unavailable.

        Args:
            confidence_range: Tuple of (lower, upper) confidence bounds in months
            language_code: Language code for localization

        Returns:
            Basic risk assessment text
        """
        lower_months = confidence_range[0]
        upper_months = confidence_range[1]

        if language_code.startswith("es"):
            risk_assessment = (
                f"La duración real que reciba beneficios puede variar entre "
                f"{lower_months:.0f} y {upper_months:.0f} meses, dependiendo de sus circunstancias específicas "
                f"como cambios en ingresos, tamaño del hogar o estado laboral. "
                f"Esta estimación se basa en patrones generales y su experiencia individual puede diferir."
            )
        else:
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
