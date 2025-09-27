"""
Tests for AI service integration with LifetimeValueService.
Tests the integration between lifetime value calculation and AI explanation generation.
"""

from unittest.mock import Mock, patch
from django.test import TestCase, override_settings
from decimal import Decimal

from programs.models import Program, ProgramDurationMultiplier, LifetimeValuePrediction
from programs.services.lifetime_value_service import LifetimeValueService
from screener.models import Screen, WhiteLabel, HouseholdMember


class TestLifetimeValueAIIntegration(TestCase):
    """Test integration between LifetimeValueService and AI communication."""

    def setUp(self):
        """Set up test data."""
        # Create white label for testing
        self.white_label = WhiteLabel.objects.create(
            name="Test Colorado", code="test_co", state_code="CO"
        )

        # Create test program
        self.snap_program = Program.objects.new_program("test_co", "test_snap")

        # Create test household screen
        self.screen = Screen.objects.create(
            white_label=self.white_label,
            completed=True,
            zipcode="80205",
            county="Denver County",
            household_size=2,
            household_assets=1000,
        )

        # Create household members
        self.head_of_household = HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
            student=False,
            pregnant=False,
            unemployed=False,
            disabled=False,
            veteran=False,
        )

        # Create duration multiplier for testing
        self.duration_multiplier = ProgramDurationMultiplier.objects.create(
            program=self.snap_program,
            white_label=self.white_label,
            average_duration_months=18.0,
            confidence_interval_lower=12.0,
            confidence_interval_upper=24.0,
            data_source="USDA Test Data 2023",
            is_active=True,
        )

        self.monthly_benefit = Decimal("300.00")

    @override_settings(AI_EXPLANATION_ENABLED=False)
    def test_ai_service_disabled(self):
        """Test that service works when AI explanations are disabled."""
        service = LifetimeValueService()

        # AI service should not be initialized
        self.assertIsNone(service.ai_service)

        # Generate prediction should still work
        prediction = service.generate_prediction(
            self.screen, self.snap_program, self.monthly_benefit
        )

        self.assertIsNotNone(prediction)
        self.assertEqual(prediction.predicted_duration_months, 18.0)
        self.assertEqual(prediction.estimated_lifetime_value, Decimal("5400.00"))
        # Should use basic explanations
        self.assertIn("families similar to yours", prediction.explanation_text)
        self.assertIn("may vary between", prediction.risk_assessment)

    @override_settings(
        AI_EXPLANATION_ENABLED=True, OPENAI_API_KEY=None, ANTHROPIC_API_KEY=None
    )
    def test_ai_service_enabled_no_keys(self):
        """Test that service falls back gracefully when AI is enabled but no API keys provided."""
        service = LifetimeValueService()

        # AI service should be initialized but without clients
        self.assertIsNotNone(service.ai_service)

        prediction = service.generate_prediction(
            self.screen, self.snap_program, self.monthly_benefit
        )

        self.assertIsNotNone(prediction)
        # Should fall back to basic explanations
        self.assertIn("families similar to yours", prediction.explanation_text)
        self.assertIn("may vary between", prediction.risk_assessment)

    @override_settings(AI_EXPLANATION_ENABLED=True, OPENAI_API_KEY="test-key")
    @patch("programs.services.ai_communication_service.openai")
    def test_ai_service_successful_generation(self, mock_openai):
        """Test successful AI explanation generation during prediction."""
        # Setup mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "AI-generated SNAP explanation"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        service = LifetimeValueService()
        prediction = service.generate_prediction(
            self.screen, self.snap_program, self.monthly_benefit
        )

        self.assertIsNotNone(prediction)
        self.assertEqual(prediction.explanation_text, "AI-generated SNAP explanation")
        self.assertEqual(prediction.risk_assessment, "AI-generated SNAP explanation")

        # Verify the prediction was saved correctly
        saved_prediction = LifetimeValuePrediction.objects.get(id=prediction.id)
        self.assertEqual(
            saved_prediction.explanation_text, "AI-generated SNAP explanation"
        )

    @override_settings(AI_EXPLANATION_ENABLED=True, OPENAI_API_KEY="test-key")
    @patch("programs.services.ai_communication_service.openai")
    def test_ai_service_failure_fallback(self, mock_openai):
        """Test that AI service failure falls back to basic explanations."""
        # Setup mock to raise exception
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.OpenAI.return_value = mock_client

        service = LifetimeValueService()
        prediction = service.generate_prediction(
            self.screen, self.snap_program, self.monthly_benefit
        )

        self.assertIsNotNone(prediction)
        # Should fall back to basic explanations
        self.assertIn("families similar to yours", prediction.explanation_text)
        self.assertIn("may vary between", prediction.risk_assessment)

    @override_settings(AI_EXPLANATION_ENABLED=True, OPENAI_API_KEY="test-key")
    @patch("programs.services.ai_communication_service.openai")
    def test_spanish_language_ai_generation(self, mock_openai):
        """Test AI explanation generation for Spanish-speaking households."""
        # Set screen language to Spanish
        self.screen.request_language_code = "es"
        self.screen.save()

        # Setup mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Explicación generada por IA"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        service = LifetimeValueService()
        prediction = service.generate_prediction(
            self.screen, self.snap_program, self.monthly_benefit
        )

        self.assertEqual(prediction.explanation_text, "Explicación generada por IA")

        # Verify the prompt was built with Spanish context
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        # Should contain Spanish template text
        self.assertIn("familias en un lenguaje claro", prompt)

    def test_ai_service_initialization_error_handling(self):
        """Test that AI service initialization errors are handled gracefully."""
        with patch(
            "programs.services.lifetime_value_service.AICommunicationService"
        ) as mock_ai:
            mock_ai.side_effect = Exception("Initialization error")

            service = LifetimeValueService()

            # Service should still be usable
            self.assertIsNone(service.ai_service)

            prediction = service.generate_prediction(
                self.screen, self.snap_program, self.monthly_benefit
            )
            self.assertIsNotNone(prediction)
            self.assertIn("families similar to yours", prediction.explanation_text)

    def test_generate_explanations_method_direct(self):
        """Test the _generate_explanations method directly."""
        service = LifetimeValueService()

        duration_data = {
            "average_duration_months": 18.0,
            "confidence_range": (12.0, 24.0),
            "data_source": "USDA Test Data 2023",
        }

        explanations = service._generate_explanations(
            screen=self.screen,
            program=self.snap_program,
            duration_data=duration_data,
            monthly_benefit=self.monthly_benefit,
            estimated_lifetime_value=Decimal("5400.00"),
        )

        self.assertIn("explanation", explanations)
        self.assertIn("risk_assessment", explanations)
        self.assertIsInstance(explanations["explanation"], str)
        self.assertIsInstance(explanations["risk_assessment"], str)

    def test_basic_explanation_spanish_integration(self):
        """Test basic explanation generation in Spanish through the service."""
        # Set screen language to Spanish
        self.screen.request_language_code = "es"
        self.screen.save()

        service = LifetimeValueService()
        prediction = service.generate_prediction(
            self.screen, self.snap_program, self.monthly_benefit
        )

        self.assertIn("familias como la suya", prediction.explanation_text)
        self.assertIn("puede variar entre", prediction.risk_assessment)

    def test_prediction_data_consistency(self):
        """Test that prediction data is consistent between calculation and explanation."""
        service = LifetimeValueService()
        prediction = service.generate_prediction(
            self.screen, self.snap_program, self.monthly_benefit
        )

        # Check that values used in explanation match calculated values
        self.assertEqual(prediction.predicted_duration_months, 18.0)
        self.assertEqual(prediction.estimated_lifetime_value, Decimal("5400.00"))
        self.assertEqual(prediction.confidence_interval_lower, 12.0)
        self.assertEqual(prediction.confidence_interval_upper, 24.0)

        # Check that these values are reflected in the explanations
        self.assertIn("18 months", prediction.explanation_text)
        self.assertIn("$5,400", prediction.explanation_text)
        self.assertIn("12 and 24 months", prediction.risk_assessment)

    @override_settings(
        AI_EXPLANATION_ENABLED=True,
        OPENAI_API_KEY="test-key",
        ANTHROPIC_API_KEY="test-key",
    )
    @patch("programs.services.ai_communication_service.openai")
    @patch("programs.services.ai_communication_service.anthropic")
    def test_provider_fallback_order(self, mock_anthropic, mock_openai):
        """Test that service tries OpenAI first, then Anthropic, then basic fallback."""
        # Setup OpenAI to fail
        mock_openai_client = Mock()
        mock_openai_client.chat.completions.create.side_effect = Exception(
            "OpenAI Error"
        )
        mock_openai.OpenAI.return_value = mock_openai_client

        # Setup Anthropic to succeed
        mock_anthropic_response = Mock()
        mock_anthropic_response.content = [Mock()]
        mock_anthropic_response.content[0].text = "Anthropic explanation"

        mock_anthropic_client = Mock()
        mock_anthropic_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic.Anthropic.return_value = mock_anthropic_client

        service = LifetimeValueService()
        prediction = service.generate_prediction(
            self.screen, self.snap_program, self.monthly_benefit
        )

        # Should use Anthropic as fallback
        self.assertEqual(prediction.explanation_text, "Anthropic explanation")

        # Verify both services were attempted
        mock_openai_client.chat.completions.create.assert_called()
        mock_anthropic_client.messages.create.assert_called()

    def test_cached_prediction_with_ai_explanations(self):
        """Test that cached predictions preserve AI-generated explanations."""
        service = LifetimeValueService()

        # Generate initial prediction
        prediction1 = service.generate_prediction(
            self.screen, self.snap_program, self.monthly_benefit
        )
        explanation1 = prediction1.explanation_text

        # Get cached prediction
        cached = service.get_cached_prediction(self.screen, self.snap_program)

        self.assertIsNotNone(cached)
        self.assertEqual(cached.explanation_text, explanation1)
        self.assertEqual(cached.id, prediction1.id)
