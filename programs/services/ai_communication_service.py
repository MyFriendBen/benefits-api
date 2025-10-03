"""
AI Communication Service for generating user-friendly explanations of lifetime benefit projections.
Integrates with multiple LLM providers (OpenAI, Anthropic) with robust fallback mechanisms.
"""

import logging
import json
from typing import Dict, Optional, Any, Union
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from django.conf import settings
from django.utils.translation import gettext as _

from programs.models import Program
from screener.models import Screen


logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class ExplanationContext:
    """Context data for generating explanations."""

    household_size: int
    program_name: str
    duration_months: float
    confidence_range: tuple[float, float]
    monthly_benefit: Decimal
    estimated_lifetime_value: Decimal
    data_source: str
    calculation_method: str = "research-based averages"
    language_code: str = "en"


class ExplanationTemplateManager:
    """
    Manages prompt templates for different types of explanations.
    Supports multi-language templates and various explanation types.
    """

    # Base templates for different explanation types
    TEMPLATES = {
        "simple_duration_explanation": {
            "en-us": """You are helping explain government benefit duration estimates to families in clear, accessible language.

Context:
- Program: {program_name}
- Household size: {household_size} people
- Estimated duration: {duration_months:.0f} months
- Confidence range: {confidence_range_lower:.0f} to {confidence_range_upper:.0f} months
- Monthly benefit: ${monthly_benefit}
- Total estimated value: ${estimated_lifetime_value:,.2f}
- Data source: {data_source}

Write a warm, encouraging explanation that:
1. Explains what this benefit estimate means in simple, clear terms
2. Mentions that this is based on research data from similar families
3. Emphasizes this is helpful for planning purposes
4. Uses short sentences and common words (8th grade reading level - avoid jargon, complex terms, or long sentences)
5. Stays under 150 words
6. IMPORTANT: Do not include any conversational phrases like "let me know if you have questions" or "I'm here to help" - this is informational content, not a chatbot

Focus on being helpful and supportive, not overwhelming with statistics. Keep language simple and direct.

OUTPUT ONLY THE EXPLANATION TEXT - no preamble like "Here's an explanation" or "This covers" - start directly with the explanation content.""",
            "es": """Estás ayudando a explicar las estimaciones de duración de beneficios gubernamentales a familias en un lenguaje claro y accesible.

Contexto:
- Programa: {program_name}
- Tamaño del hogar: {household_size} personas
- Duración estimada: {duration_months:.0f} meses
- Rango de confianza: {confidence_range_lower:.0f} a {confidence_range_upper:.0f} meses
- Beneficio mensual: ${monthly_benefit}
- Valor total estimado: ${estimated_lifetime_value:,.2f}
- Fuente de datos: {data_source}

Escribe una explicación cálida y alentadora que:
1. Explique qué significa esta estimación de beneficios en términos simples y claros
2. Mencione que esto se basa en datos de investigación de familias similares
3. Enfatice que esto es útil para propósitos de planificación
4. Use oraciones cortas y palabras comunes (nivel de lectura de 8vo grado - evita jerga, términos complejos u oraciones largas)
5. Se mantenga bajo 150 palabras
6. IMPORTANTE: No incluyas frases conversacionales como "déjame saber si tienes preguntas" o "estoy aquí para ayudar" - este es contenido informativo, no un chatbot

Enfócate en ser útil y de apoyo, no abrumador con estadísticas. Mantén el lenguaje simple y directo.

ESCRIBE SOLO EL TEXTO DE LA EXPLICACIÓN - sin preámbulo como "Aquí está una explicación" o "Esto cubre" - comienza directamente con el contenido de la explicación.""",
        },
        "risk_assessment": {
            "en-us": """You are explaining potential factors that might affect benefit duration to help families understand uncertainty.

Context:
- Program: {program_name}
- Estimated duration: {duration_months:.0f} months
- Confidence range: {confidence_range_lower:.0f} to {confidence_range_upper:.0f} months

Write a brief, reassuring explanation that:
1. Acknowledges that individual circumstances vary
2. Mentions 2-3 common factors that might affect duration (income changes, household changes, work status)
3. Emphasizes that this estimate helps with planning
4. Uses encouraging tone and simple language (8th grade reading level - short sentences, common words)
5. Stays under 100 words
6. IMPORTANT: Do not include conversational phrases like "let me know" or "I'm here to help" - this is informational content only

Focus on being informative without causing anxiety. Keep language clear and easy to understand.

OUTPUT ONLY THE EXPLANATION TEXT - no preamble like "Here's what you should know" - start directly with the explanation content.""",
            "es": """Estás explicando factores potenciales que podrían afectar la duración de beneficios para ayudar a las familias a entender la incertidumbre.

Contexto:
- Programa: {program_name}
- Duración estimada: {duration_months:.0f} meses
- Rango de confianza: {confidence_range_lower:.0f} a {confidence_range_upper:.0f} meses

Escribe una explicación breve y tranquilizadora que:
1. Reconozca que las circunstancias individuales varían
2. Mencione 2-3 factores comunes que podrían afectar la duración (cambios de ingresos, cambios en el hogar, estado laboral)
3. Enfatice que esta estimación ayuda con la planificación
4. Use un tono alentador y lenguaje simple (nivel de lectura de 8vo grado - oraciones cortas, palabras comunes)
5. Se mantenga bajo 100 palabras
6. IMPORTANTE: No incluyas frases conversacionales como "déjame saber" o "estoy aquí para ayudar" - este es solo contenido informativo

Enfócate en ser informativo sin causar ansiedad. Mantén el lenguaje claro y fácil de entender.

ESCRIBE SOLO EL TEXTO DE LA EXPLICACIÓN - sin preámbulo como "Aquí está lo que debes saber" - comienza directamente con el contenido de la explicación.""",
        },
    }

    def build_prompt(self, template_type: str, context: ExplanationContext) -> str:
        """
        Build a prompt for the specified template type and context.

        Args:
            template_type: Type of explanation template to use
            context: Context data for the explanation

        Returns:
            Formatted prompt string

        Raises:
            ValueError: If template type or language not supported
        """
        if template_type not in self.TEMPLATES:
            raise ValueError(f"Unsupported template type: {template_type}")

        templates = self.TEMPLATES[template_type]
        language_code = context.language_code

        # Fallback to English if language not supported
        if language_code not in templates:
            logger.warning(
                f"Language {language_code} not supported for {template_type}, falling back to English"
            )
            language_code = "en"

        template = templates[language_code]

        # Format template with context data
        try:
            return template.format(
                program_name=context.program_name,
                household_size=context.household_size,
                duration_months=context.duration_months,
                confidence_range_lower=context.confidence_range[0],
                confidence_range_upper=context.confidence_range[1],
                monthly_benefit=context.monthly_benefit,
                estimated_lifetime_value=context.estimated_lifetime_value,
                data_source=context.data_source,
                calculation_method=context.calculation_method,
            )
        except KeyError as e:
            logger.error(f"Missing context key for template formatting: {e}")
            raise ValueError(
                f"Invalid context for template {template_type}: missing {e}"
            )


class AICommunicationService:
    """
    Generates user-friendly explanations using LLMs.
    Supports multiple providers with automatic fallback and comprehensive error handling.
    """

    def __init__(self):
        self.template_manager = ExplanationTemplateManager()
        self._openai_client = None
        self._anthropic_client = None

    def _get_openai_client(self):
        """Lazy initialization of OpenAI client."""
        logger.info(f"🔍 _get_openai_client called: _openai_client={self._openai_client}")
        logger.info(f"🔍 OPENAI_API_KEY configured: {hasattr(settings, 'OPENAI_API_KEY') and bool(settings.OPENAI_API_KEY)}")

        if (
            self._openai_client is None
            and hasattr(settings, "OPENAI_API_KEY")
            and settings.OPENAI_API_KEY
        ):
            logger.info("🔍 Attempting to initialize OpenAI client...")
            try:
                import openai
                logger.info("🔍 OpenAI package imported successfully")

                # Log API key format (masked for security)
                api_key = settings.OPENAI_API_KEY
                if api_key:
                    logger.info(f"🔍 API key format: {api_key[:7]}...{api_key[-4:]} (length: {len(api_key)})")
                else:
                    logger.error("🔍 API key is empty!")

                self._openai_client = openai.OpenAI(api_key=api_key)
                logger.info("✅ OpenAI client initialized successfully")
            except ImportError:
                logger.warning(
                    "OpenAI package not installed, OpenAI provider unavailable"
                )
            except Exception as e:
                import traceback
                logger.error(f"Failed to initialize OpenAI client: {e}")
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
        else:
            logger.info(f"🔍 Skipping OpenAI initialization: client_exists={self._openai_client is not None}, has_key={hasattr(settings, 'OPENAI_API_KEY') and bool(settings.OPENAI_API_KEY)}")

        logger.info(f"🔍 Returning OpenAI client: {self._openai_client}")
        return self._openai_client

    def _get_anthropic_client(self):
        """Lazy initialization of Anthropic client."""
        if (
            self._anthropic_client is None
            and hasattr(settings, "ANTHROPIC_API_KEY")
            and settings.ANTHROPIC_API_KEY
        ):
            try:
                import anthropic

                self._anthropic_client = anthropic.Anthropic(
                    api_key=settings.ANTHROPIC_API_KEY
                )
            except ImportError:
                logger.warning(
                    "Anthropic package not installed, Anthropic provider unavailable"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
        return self._anthropic_client

    def _call_openai(self, prompt: str, max_tokens: int = 200) -> Optional[str]:
        """Make API call to OpenAI."""
        logger.info("🔍 _call_openai called")
        client = self._get_openai_client()
        logger.info(f"🔍 OpenAI client after _get_openai_client: {client}")
        if not client:
            logger.info("🔍 No OpenAI client available, returning None")
            return None

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
                timeout=10,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}")
            return None

    def _call_anthropic(self, prompt: str, max_tokens: int = 200) -> Optional[str]:
        """Make API call to Anthropic."""
        client = self._get_anthropic_client()
        if not client:
            return None

        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=max_tokens,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}],
                timeout=10,
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.warning(f"Anthropic API call failed: {e}")
            return None

    def _generate_with_fallback(
        self,
        prompt: str,
        context: ExplanationContext,
        explanation_type: str = "explanation",
    ) -> str:
        """
        Generate text using LLM with fallback to basic explanation.

        Args:
            prompt: The formatted prompt to send to the LLM
            context: Context data for fallback generation
            explanation_type: Type of explanation for fallback generation

        Returns:
            Generated explanation text
        """
        # Try primary provider (Anthropic)
        result = self._call_anthropic(prompt)
        if result:
            logger.info("Generated explanation using Anthropic")
            return result

        # Try secondary provider (OpenAI)
        result = self._call_openai(prompt)
        if result:
            logger.info("Generated explanation using OpenAI")
            return result

        # Fallback to basic explanation
        logger.warning("All LLM providers failed, falling back to basic explanation")
        if explanation_type == "risk_assessment":
            return self._generate_basic_risk_assessment(context)
        else:
            return self._generate_basic_explanation(context)

    def _generate_basic_explanation(self, context: ExplanationContext) -> str:
        """Generate basic explanation without LLM (fallback)."""
        if context.language_code.startswith("es"):
            return (
                f"Basado en datos de investigación de {context.data_source}, las familias como la suya "
                f"típicamente reciben beneficios de {context.program_name} durante aproximadamente "
                f"{context.duration_months:.0f} meses. Con su beneficio mensual de ${context.monthly_benefit}, "
                f"esto podría proporcionar aproximadamente ${context.estimated_lifetime_value:,.2f} "
                f"en asistencia alimentaria total a lo largo del tiempo. Esta estimación le ayuda a "
                f"entender el valor potencial a largo plazo de este programa de beneficios."
            )
        else:
            return (
                f"Based on research data from {context.data_source}, families similar to yours typically "
                f"receive {context.program_name} benefits for about {context.duration_months:.0f} months. "
                f"With your monthly benefit of ${context.monthly_benefit}, this could provide "
                f"approximately ${context.estimated_lifetime_value:,.2f} in total food assistance over time. "
                f"This estimate helps you understand the potential long-term value of this benefit program."
            )

    def _generate_basic_risk_assessment(self, context: ExplanationContext) -> str:
        """Generate basic risk assessment without LLM (fallback)."""
        lower_months = context.confidence_range[0]
        upper_months = context.confidence_range[1]

        if context.language_code.startswith("es"):
            return (
                f"La duración real que reciba beneficios puede variar entre "
                f"{lower_months:.0f} y {upper_months:.0f} meses, dependiendo de sus circunstancias específicas "
                f"como cambios en ingresos, tamaño del hogar o estado laboral. "
                f"Esta estimación se basa en patrones generales y su experiencia individual puede diferir."
            )
        else:
            return (
                f"The actual duration you receive benefits may vary between "
                f"{lower_months:.0f} and {upper_months:.0f} months, depending on your specific circumstances "
                f"such as changes in income, household size, or work status. "
                f"This estimate is based on general patterns and your individual experience may differ."
            )

    def generate_explanation(
        self, lifetime_data: Dict[str, Any], screen: Screen, program: Program
    ) -> Dict[str, str]:
        """
        Generate user-friendly explanation for lifetime benefit projection.

        Args:
            lifetime_data: Dictionary containing duration and value predictions
            screen: The household screen data
            program: The benefit program

        Returns:
            Dictionary with 'explanation' and 'risk_assessment' keys
        """
        # Build context for explanation generation
        context = ExplanationContext(
            household_size=screen.household_size or 1,
            program_name=getattr(program.name, "text", program.name_abbreviated),
            duration_months=lifetime_data["predicted_duration_months"],
            confidence_range=(
                lifetime_data["confidence_interval_lower"],
                lifetime_data["confidence_interval_upper"],
            ),
            monthly_benefit=lifetime_data.get("monthly_benefit", Decimal("0")),
            estimated_lifetime_value=lifetime_data["estimated_lifetime_value"],
            data_source=lifetime_data.get("data_source", "research data"),
            language_code=screen.get_language_code(),
        )

        # Generate main explanation
        explanation_prompt = self.template_manager.build_prompt(
            "simple_duration_explanation", context
        )
        explanation = self._generate_with_fallback(
            explanation_prompt, context, "explanation"
        )

        # Generate risk assessment
        risk_prompt = self.template_manager.build_prompt("risk_assessment", context)
        risk_assessment = self._generate_with_fallback(
            risk_prompt, context, "risk_assessment"
        )

        return {"explanation": explanation, "risk_assessment": risk_assessment}

    def health_check(self) -> Dict[str, bool]:
        """
        Check the health/availability of AI services.

        Returns:
            Dictionary with provider availability status
        """
        return {
            "openai_available": self._get_openai_client() is not None,
            "anthropic_available": self._get_anthropic_client() is not None,
            "templates_loaded": len(self.template_manager.TEMPLATES) > 0,
        }
