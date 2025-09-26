"""
Example usage of the AI Communication Service for lifetime benefit explanations.

This file demonstrates how to use the new AI explanation service that was integrated
with the lifetime value calculation system.
"""

from decimal import Decimal
from django.conf import settings
from programs.services.ai_communication_service import AICommunicationService
from programs.services.lifetime_value_service import LifetimeValueService
from programs.models import Program, ProgramDurationMultiplier
from screener.models import Screen, WhiteLabel


def example_basic_usage():
    """Example of basic AI service usage."""
    # Initialize the AI service
    ai_service = AICommunicationService()

    # Check service health
    health = ai_service.health_check()
    print("AI Service Health:", health)

    # Example lifetime data
    lifetime_data = {
        'predicted_duration_months': 18.0,
        'confidence_interval_lower': 12.0,
        'confidence_interval_upper': 24.0,
        'estimated_lifetime_value': Decimal('5400.00'),
        'monthly_benefit': Decimal('300.00'),
        'data_source': 'USDA Research 2023'
    }

    # Mock screen and program (in real usage, these would come from the database)
    class MockScreen:
        household_size = 2
        def get_language_code(self):
            return 'en'

    class MockProgram:
        name_abbreviated = 'SNAP'
        class name:
            text = 'SNAP Food Assistance'

    screen = MockScreen()
    program = MockProgram()

    # Generate explanations
    explanations = ai_service.generate_explanation(lifetime_data, screen, program)

    print("\nGenerated Explanation:")
    print(explanations['explanation'])
    print("\nGenerated Risk Assessment:")
    print(explanations['risk_assessment'])


def example_lifetime_value_service_integration():
    """Example of using the integrated LifetimeValueService with AI explanations."""

    # This would typically be called from a view or API endpoint
    # after calculating eligibility and monthly benefits

    try:
        # Get a white label and program (example assumes they exist)
        white_label = WhiteLabel.objects.get(code='test_co')
        program = Program.objects.filter(name_abbreviated__icontains='snap').first()

        if not program:
            print("No SNAP program found for example")
            return

        # Create a sample screen
        screen = Screen.objects.create(
            white_label=white_label,
            household_size=3,
            zipcode='80205',
            county='Denver County',
            completed=True
        )

        # Ensure duration multiplier exists
        duration_multiplier, created = ProgramDurationMultiplier.objects.get_or_create(
            program=program,
            white_label=white_label,
            defaults={
                'average_duration_months': 24.0,
                'confidence_interval_lower': 18.0,
                'confidence_interval_upper': 30.0,
                'data_source': 'USDA Research 2023',
                'is_active': True
            }
        )

        # Initialize lifetime value service (with AI integration)
        service = LifetimeValueService()

        # Generate prediction with AI explanations
        monthly_benefit = Decimal('450.00')
        prediction = service.generate_prediction(screen, program, monthly_benefit)

        print(f"\nLifetime Value Prediction for {program.name_abbreviated}:")
        print(f"Duration: {prediction.predicted_duration_months} months")
        print(f"Lifetime Value: ${prediction.estimated_lifetime_value}")
        print(f"\nAI-Generated Explanation:")
        print(prediction.explanation_text)
        print(f"\nRisk Assessment:")
        print(prediction.risk_assessment)

        # Clean up example data
        prediction.delete()
        screen.delete()
        if created:
            duration_multiplier.delete()

    except Exception as e:
        print(f"Error in example: {e}")


def example_spanish_language_support():
    """Example of Spanish language explanation generation."""

    ai_service = AICommunicationService()

    # Example with Spanish language context
    lifetime_data = {
        'predicted_duration_months': 20.0,
        'confidence_interval_lower': 15.0,
        'confidence_interval_upper': 25.0,
        'estimated_lifetime_value': Decimal('6000.00'),
        'monthly_benefit': Decimal('300.00'),
        'data_source': 'Datos USDA 2023'
    }

    class MockSpanishScreen:
        household_size = 4
        def get_language_code(self):
            return 'es'  # Spanish

    class MockProgram:
        name_abbreviated = 'SNAP'
        class name:
            text = 'Asistencia Alimentaria SNAP'

    screen = MockSpanishScreen()
    program = MockProgram()

    explanations = ai_service.generate_explanation(lifetime_data, screen, program)

    print("\n=== Spanish Language Example ===")
    print("Explicación Generada:")
    print(explanations['explanation'])
    print("\nEvaluación de Riesgo:")
    print(explanations['risk_assessment'])


def example_configuration_check():
    """Example of checking AI service configuration."""

    print("=== AI Service Configuration ===")
    print(f"AI Explanations Enabled: {getattr(settings, 'AI_EXPLANATION_ENABLED', True)}")
    print(f"OpenAI API Key Configured: {'Yes' if getattr(settings, 'OPENAI_API_KEY', None) else 'No'}")
    print(f"Anthropic API Key Configured: {'Yes' if getattr(settings, 'ANTHROPIC_API_KEY', None) else 'No'}")
    print(f"AI Timeout Setting: {getattr(settings, 'AI_EXPLANATION_TIMEOUT', 10)} seconds")


if __name__ == "__main__":
    print("AI Communication Service Examples")
    print("=" * 40)

    # Run configuration check
    example_configuration_check()
    print()

    # Run basic usage example
    print("1. Basic AI Service Usage:")
    example_basic_usage()
    print()

    # Run Spanish language example
    print("2. Spanish Language Support:")
    example_spanish_language_support()
    print()

    # Note: The integrated service example requires database setup
    print("3. Integrated Service Example:")
    print("(Run this in Django shell with proper database setup)")
    print("example_lifetime_value_service_integration()")