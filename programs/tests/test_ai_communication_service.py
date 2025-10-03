"""
Tests for the AI Communication Service.
Tests both successful AI generation and fallback scenarios.
"""

from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from decimal import Decimal

from programs.models import Program, ProgramDurationMultiplier
from programs.services.ai_communication_service import (
    AICommunicationService,
    ExplanationTemplateManager,
    ExplanationContext,
    LLMProvider,
)
from screener.models import Screen, WhiteLabel, HouseholdMember


class TestExplanationTemplateManager(TestCase):
    """Test the template management functionality."""

    def setUp(self):
        self.template_manager = ExplanationTemplateManager()

    def test_build_prompt_simple_explanation_english(self):
        """Test building a simple explanation prompt in English."""
        context = ExplanationContext(
            household_size=2,
            program_name="SNAP",
            duration_months=18.0,
            confidence_range=(12.0, 24.0),
            monthly_benefit=Decimal("300"),
            estimated_lifetime_value=Decimal("5400"),
            data_source="USDA Research 2023",
            language_code="en",
        )

        prompt = self.template_manager.build_prompt(
            "simple_duration_explanation", context
        )

        self.assertIn("SNAP", prompt)
        self.assertIn("18 months", prompt)
        self.assertIn("2 people", prompt)
        self.assertIn("$300", prompt)
        self.assertIn("$5,400", prompt)
        self.assertIn("USDA Research 2023", prompt)

    def test_build_prompt_simple_explanation_spanish(self):
        """Test building a simple explanation prompt in Spanish."""
        context = ExplanationContext(
            household_size=3,
            program_name="SNAP",
            duration_months=24.0,
            confidence_range=(18.0, 30.0),
            monthly_benefit=Decimal("450"),
            estimated_lifetime_value=Decimal("10800"),
            data_source="Datos USDA 2023",
            language_code="es",
        )

        prompt = self.template_manager.build_prompt(
            "simple_duration_explanation", context
        )

        self.assertIn("SNAP", prompt)
        self.assertIn("24 meses", prompt)
        self.assertIn("3 personas", prompt)
        self.assertIn("$450", prompt)
        self.assertIn("$10,800", prompt)
        self.assertIn("Datos USDA 2023", prompt)

    def test_build_prompt_risk_assessment_english(self):
        """Test building a risk assessment prompt in English."""
        context = ExplanationContext(
            household_size=2,
            program_name="SNAP",
            duration_months=18.0,
            confidence_range=(12.0, 24.0),
            monthly_benefit=Decimal("300"),
            estimated_lifetime_value=Decimal("5400"),
            data_source="USDA Research 2023",
        )

        prompt = self.template_manager.build_prompt("risk_assessment", context)

        self.assertIn("18 months", prompt)
        self.assertIn("12 to 24 months", prompt)
        self.assertIn("SNAP", prompt)

    def test_build_prompt_unsupported_template(self):
        """Test that unsupported template type raises ValueError."""
        context = ExplanationContext(
            household_size=2,
            program_name="SNAP",
            duration_months=18.0,
            confidence_range=(12.0, 24.0),
            monthly_benefit=Decimal("300"),
            estimated_lifetime_value=Decimal("5400"),
            data_source="USDA Research 2023",
        )

        with self.assertRaises(ValueError) as cm:
            self.template_manager.build_prompt("unsupported_template", context)

        self.assertIn("Unsupported template type", str(cm.exception))

    def test_build_prompt_unsupported_language_fallback(self):
        """Test that unsupported language falls back to English."""
        context = ExplanationContext(
            household_size=2,
            program_name="SNAP",
            duration_months=18.0,
            confidence_range=(12.0, 24.0),
            monthly_benefit=Decimal("300"),
            estimated_lifetime_value=Decimal("5400"),
            data_source="USDA Research 2023",
            language_code="fr",  # French not supported
        )

        prompt = self.template_manager.build_prompt(
            "simple_duration_explanation", context
        )

        # Should contain English text
        self.assertIn("helping explain", prompt)
        self.assertNotIn("expliquer", prompt)  # No French


class TestAICommunicationService(TestCase):
    """Test the AI Communication Service functionality."""

    def setUp(self):
        """Set up test data."""
        # Create test white label and screen
        self.white_label = WhiteLabel.objects.create(
            name="Test Colorado", code="test_co", state_code="CO"
        )

        self.screen = Screen.objects.create(
            white_label=self.white_label,
            completed=True,
            zipcode="80205",
            county="Denver County",
            household_size=2,
            household_assets=1000,
        )

        # Add head of household for language code method
        HouseholdMember.objects.create(
            screen=self.screen,
            relationship="headOfHousehold",
            age=35,
            student=False,
            pregnant=False,
            unemployed=False,
            disabled=False,
            veteran=False,
        )

        # Create test program
        self.program = Program.objects.new_program("test_co", "test_snap")

        # Test lifetime data
        self.lifetime_data = {
            "predicted_duration_months": 18.0,
            "confidence_interval_lower": 12.0,
            "confidence_interval_upper": 24.0,
            "estimated_lifetime_value": Decimal("5400"),
            "monthly_benefit": Decimal("300"),
            "data_source": "USDA Research 2023",
        }

    @override_settings(OPENAI_API_KEY=None, ANTHROPIC_API_KEY=None)
    def test_initialization_no_api_keys(self):
        """Test service initializes gracefully without API keys."""
        service = AICommunicationService()

        self.assertIsNotNone(service.template_manager)
        self.assertIsNone(service._openai_client)
        self.assertIsNone(service._anthropic_client)

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("programs.services.ai_communication_service.openai")
    def test_openai_client_initialization(self, mock_openai):
        """Test OpenAI client initialization."""
        mock_client = Mock()
        mock_openai.OpenAI.return_value = mock_client

        service = AICommunicationService()
        client = service._get_openai_client()

        self.assertEqual(client, mock_client)
        mock_openai.OpenAI.assert_called_once_with(api_key="test-key")

    @override_settings(ANTHROPIC_API_KEY="test-key")
    @patch("programs.services.ai_communication_service.anthropic")
    def test_anthropic_client_initialization(self, mock_anthropic):
        """Test Anthropic client initialization."""
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        service = AICommunicationService()
        client = service._get_anthropic_client()

        self.assertEqual(client, mock_client)
        mock_anthropic.Anthropic.assert_called_once_with(api_key="test-key")

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("programs.services.ai_communication_service.openai")
    def test_openai_api_call_success(self, mock_openai):
        """Test successful OpenAI API call."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated explanation text"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        service = AICommunicationService()
        result = service._call_openai("test prompt")

        self.assertEqual(result, "Generated explanation text")
        mock_client.chat.completions.create.assert_called_once()

    @override_settings(ANTHROPIC_API_KEY="test-key")
    @patch("programs.services.ai_communication_service.anthropic")
    def test_anthropic_api_call_success(self, mock_anthropic):
        """Test successful Anthropic API call."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Generated explanation text"

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        service = AICommunicationService()
        result = service._call_anthropic("test prompt")

        self.assertEqual(result, "Generated explanation text")
        mock_client.messages.create.assert_called_once()

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("programs.services.ai_communication_service.openai")
    def test_openai_api_call_failure_fallback(self, mock_openai):
        """Test OpenAI API failure falls back to basic explanation."""
        # Setup mock to raise exception
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai.OpenAI.return_value = mock_client

        service = AICommunicationService()
        result = service._call_openai("test prompt")

        self.assertIsNone(result)

    def test_generate_explanation_fallback_to_basic(self):
        """Test that explanation generation falls back to basic when no AI services available."""
        service = AICommunicationService()

        result = service.generate_explanation(
            self.lifetime_data, self.screen, self.program
        )

        self.assertIn("explanation", result)
        self.assertIn("risk_assessment", result)
        self.assertIn("families similar to yours", result["explanation"])
        self.assertIn("may vary between", result["risk_assessment"])

    @override_settings(OPENAI_API_KEY="test-key")
    @patch("programs.services.ai_communication_service.openai")
    def test_generate_explanation_with_openai_success(self, mock_openai):
        """Test successful explanation generation using OpenAI."""
        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "AI-generated explanation"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        service = AICommunicationService()
        result = service.generate_explanation(
            self.lifetime_data, self.screen, self.program
        )

        self.assertEqual(result["explanation"], "AI-generated explanation")
        self.assertEqual(result["risk_assessment"], "AI-generated explanation")

    def test_generate_explanation_spanish_fallback(self):
        """Test basic explanation generation in Spanish."""
        # Set screen language to Spanish
        self.screen.request_language_code = "es"
        self.screen.save()

        service = AICommunicationService()
        result = service.generate_explanation(
            self.lifetime_data, self.screen, self.program
        )

        self.assertIn("familias como la suya", result["explanation"])
        self.assertIn("puede variar entre", result["risk_assessment"])

    def test_health_check_no_services(self):
        """Test health check with no AI services configured."""
        service = AICommunicationService()
        health = service.health_check()

        self.assertFalse(health["openai_available"])
        self.assertFalse(health["anthropic_available"])
        self.assertTrue(health["templates_loaded"])

    @override_settings(OPENAI_API_KEY="test-key", ANTHROPIC_API_KEY="test-key")
    @patch("programs.services.ai_communication_service.openai")
    @patch("programs.services.ai_communication_service.anthropic")
    def test_health_check_with_services(self, mock_anthropic, mock_openai):
        """Test health check with AI services configured."""
        mock_openai.OpenAI.return_value = Mock()
        mock_anthropic.Anthropic.return_value = Mock()

        service = AICommunicationService()
        health = service.health_check()

        self.assertTrue(health["openai_available"])
        self.assertTrue(health["anthropic_available"])
        self.assertTrue(health["templates_loaded"])


class TestExplanationContext(TestCase):
    """Test the ExplanationContext dataclass."""

    def test_context_creation(self):
        """Test creating an ExplanationContext instance."""
        context = ExplanationContext(
            household_size=2,
            program_name="SNAP",
            duration_months=18.0,
            confidence_range=(12.0, 24.0),
            monthly_benefit=Decimal("300"),
            estimated_lifetime_value=Decimal("5400"),
            data_source="USDA Research 2023",
            language_code="en",
        )

        self.assertEqual(context.household_size, 2)
        self.assertEqual(context.program_name, "SNAP")
        self.assertEqual(context.duration_months, 18.0)
        self.assertEqual(context.confidence_range, (12.0, 24.0))
        self.assertEqual(context.monthly_benefit, Decimal("300"))
        self.assertEqual(context.estimated_lifetime_value, Decimal("5400"))
        self.assertEqual(context.data_source, "USDA Research 2023")
        self.assertEqual(context.language_code, "en")

    def test_context_defaults(self):
        """Test default values in ExplanationContext."""
        context = ExplanationContext(
            household_size=1,
            program_name="SNAP",
            duration_months=12.0,
            confidence_range=(8.0, 16.0),
            monthly_benefit=Decimal("200"),
            estimated_lifetime_value=Decimal("2400"),
            data_source="Test Data",
        )

        self.assertEqual(context.calculation_method, "research-based averages")
        self.assertEqual(context.language_code, "en")
