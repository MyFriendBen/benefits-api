"""
Tests for the check_readability management command.

These tests verify that the readability checker correctly analyzes
English and Spanish text using various readability metrics.
"""

import pytest
from io import StringIO
from unittest.mock import patch, MagicMock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from translations.management.commands.check_readability import (
    ReadabilityChecker,
    ReadabilityResult,
)


class ReadabilityCheckerTest(TestCase):
    """Tests for the ReadabilityChecker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.checker = ReadabilityChecker()

    def test_default_thresholds(self):
        """Test that default thresholds are set correctly."""
        self.assertEqual(self.checker.en_threshold, 8.0)
        self.assertEqual(self.checker.es_threshold, 60.0)

    def test_custom_thresholds(self):
        """Test that custom thresholds can be set."""
        checker = ReadabilityChecker(en_threshold=6.0, es_threshold=70.0)
        self.assertEqual(checker.en_threshold, 6.0)
        self.assertEqual(checker.es_threshold, 70.0)

    def test_analyze_english_simple_text(self):
        """Test analyzing simple English text."""
        text = "This is a simple sentence. It is easy to read. Anyone can understand it."
        scores = self.checker.analyze_english(text)

        self.assertIn("flesch_reading_ease", scores)
        self.assertIn("flesch_kincaid_grade", scores)
        self.assertIn("smog_index", scores)
        self.assertIn("automated_readability_index", scores)

        # Simple text should have low grade level
        self.assertLess(scores["flesch_kincaid_grade"], 10)

    def test_analyze_english_complex_text(self):
        """Test analyzing complex English text."""
        text = """
        The implementation of sophisticated algorithmic methodologies necessitates 
        a comprehensive understanding of computational complexity theory and 
        asymptotic analysis. Furthermore, the utilization of advanced data structures 
        facilitates optimal performance characteristics in enterprise-grade applications.
        """
        scores = self.checker.analyze_english(text)

        # Complex text should have higher grade level
        self.assertGreater(scores["flesch_kincaid_grade"], 10)

    def test_analyze_spanish_text(self):
        """Test analyzing Spanish text."""
        text = "Esta es una oración simple. Es fácil de leer. Cualquiera puede entenderla."
        scores = self.checker.analyze_spanish(text)

        self.assertIn("fernandez_huerta", scores)
        self.assertIn("szigriszt_pazos", scores)
        self.assertIn("crawford", scores)

    def test_check_english_passing(self):
        """Test that simple English text passes readability check."""
        text = "This is a simple sentence. It is easy to read. Anyone can understand it."
        result = self.checker.check("test.label", text, "en-us")

        self.assertEqual(result.label, "test.label")
        self.assertEqual(result.language, "en-us")
        self.assertGreater(result.word_count, 0)
        # Simple text should pass with default threshold
        self.assertTrue(result.passes)

    def test_check_english_failing(self):
        """Test that complex English text fails readability check."""
        text = """
        The implementation of sophisticated algorithmic methodologies necessitates 
        a comprehensive understanding of computational complexity theory and 
        asymptotic analysis. Furthermore, the utilization of advanced data structures 
        facilitates optimal performance characteristics in enterprise-grade applications.
        The paradigmatic shift in technological infrastructure demands meticulous 
        consideration of architectural patterns and systematic decomposition strategies.
        """
        result = self.checker.check("test.label", text, "en-us")

        # Complex text should fail with default threshold
        self.assertFalse(result.passes)
        self.assertGreater(result.primary_score, 8.0)

    def test_check_short_text_passes(self):
        """Test that very short text is skipped and passes by default."""
        text = "Hello world"  # Only 2 words
        result = self.checker.check("test.label", text, "en-us")

        self.assertTrue(result.passes)
        self.assertEqual(result.word_count, 2)
        self.assertEqual(result.scores, {})

    def test_check_empty_text_passes(self):
        """Test that empty text passes by default."""
        result = self.checker.check("test.label", "", "en-us")

        self.assertTrue(result.passes)
        self.assertEqual(result.word_count, 0)

    def test_check_none_text_passes(self):
        """Test that None text passes by default."""
        result = self.checker.check("test.label", None, "en-us")

        self.assertTrue(result.passes)
        self.assertEqual(result.word_count, 0)

    def test_check_spanish_text(self):
        """Test checking Spanish text uses correct metrics."""
        text = """
        Esta es una oración de prueba para verificar la legibilidad del texto. 
        El contenido debe ser fácil de entender para todos los lectores.
        Queremos asegurarnos de que el texto sea accesible para todos.
        """
        result = self.checker.check("test.label", text, "es")

        self.assertEqual(result.language, "es")
        self.assertIn("fernandez_huerta", result.scores)
        # Threshold comparison is opposite for Spanish (higher is better)
        self.assertEqual(result.threshold, 60.0)

    def test_word_count(self):
        """Test word counting."""
        self.assertEqual(self.checker.get_word_count(""), 0)
        self.assertEqual(self.checker.get_word_count("one"), 1)
        self.assertEqual(self.checker.get_word_count("one two three"), 3)
        self.assertEqual(self.checker.get_word_count("  spaced   words  "), 2)


class CheckReadabilityCommandTest(TestCase):
    """Tests for the check_readability management command."""

    def setUp(self):
        """Set up test fixtures."""
        self.out = StringIO()
        self.err = StringIO()

    @patch("translations.management.commands.check_readability.Translation")
    def test_command_runs_without_error(self, mock_translation_class):
        """Test that the command runs without errors."""
        # Set up mock
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.prefetch_related.return_value = mock_queryset
        mock_queryset.count.return_value = 0
        mock_queryset.__iter__ = lambda self: iter([])
        mock_translation_class.objects = mock_queryset

        call_command("check_readability", stdout=self.out, stderr=self.err)

        output = self.out.getvalue()
        self.assertIn("READABILITY ANALYSIS REPORT", output)

    @patch("translations.management.commands.check_readability.Translation")
    def test_command_with_language_option(self, mock_translation_class):
        """Test that the command respects the language option."""
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.prefetch_related.return_value = mock_queryset
        mock_queryset.count.return_value = 0
        mock_queryset.__iter__ = lambda self: iter([])
        mock_translation_class.objects = mock_queryset

        call_command("check_readability", "--language", "es", stdout=self.out)

        output = self.out.getvalue()
        self.assertIn("Language: es", output)
        self.assertIn("Fernández-Huerta", output)

    @patch("translations.management.commands.check_readability.Translation")
    def test_command_with_threshold_option(self, mock_translation_class):
        """Test that the command respects custom threshold."""
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.prefetch_related.return_value = mock_queryset
        mock_queryset.count.return_value = 0
        mock_queryset.__iter__ = lambda self: iter([])
        mock_translation_class.objects = mock_queryset

        call_command("check_readability", "--threshold", "6.0", stdout=self.out)

        output = self.out.getvalue()
        self.assertIn("Threshold: <= 6.0", output)

    @patch("translations.management.commands.check_readability.WhiteLabel")
    @patch("translations.management.commands.check_readability.Program")
    @patch("translations.management.commands.check_readability.Translation")
    def test_command_with_whitelabel_option(self, mock_translation_class, mock_program_class, mock_whitelabel_class):
        """Test that the command respects the whitelabel option."""
        # Set up white label mock
        mock_wl = MagicMock()
        mock_whitelabel_class.objects.get.return_value = mock_wl
        mock_whitelabel_class.DoesNotExist = Exception

        # Set up program mock with translation field
        mock_translation = MagicMock()
        mock_translation.label = "program.test_1-name"
        mock_program = MagicMock()
        mock_program.name = mock_translation
        mock_program_class.objects.filter.return_value = [mock_program]

        # Set up translation mock
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.prefetch_related.return_value = mock_queryset
        mock_queryset.count.return_value = 0
        mock_queryset.__iter__ = lambda self: iter([])
        mock_translation_class.objects = mock_queryset

        call_command("check_readability", "--whitelabel", "co", stdout=self.out)

        output = self.out.getvalue()
        self.assertIn("White Label: co", output)

    @patch("translations.management.commands.check_readability.Translation")
    def test_command_fail_on_error_with_failures(self, mock_translation_class):
        """Test that --fail-on-error raises CommandError when there are failures."""
        # Create a mock translation with complex text that will fail
        mock_translation = MagicMock()
        mock_translation.label = "test.complex"
        mock_translation.text = """
        The implementation of sophisticated algorithmic methodologies necessitates 
        a comprehensive understanding of computational complexity theory and 
        asymptotic analysis. Furthermore, the utilization of advanced data structures 
        facilitates optimal performance characteristics in enterprise-grade applications.
        The paradigmatic shift in technological infrastructure demands meticulous 
        consideration of architectural patterns and systematic decomposition strategies.
        """

        mock_queryset = MagicMock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.prefetch_related.return_value = mock_queryset
        mock_queryset.count.return_value = 1
        mock_queryset.__iter__ = lambda self: iter([mock_translation])
        mock_translation_class.objects = mock_queryset

        with self.assertRaises(CommandError) as context:
            call_command("check_readability", "--fail-on-error", stdout=self.out)

        self.assertIn("failed readability check", str(context.exception))


class ReadabilityResultTest(TestCase):
    """Tests for the ReadabilityResult dataclass."""

    def test_result_creation(self):
        """Test creating a ReadabilityResult."""
        result = ReadabilityResult(
            label="test.label",
            text="Test text",
            language="en-us",
            scores={"flesch_kincaid_grade": 5.0},
            passes=True,
            primary_score=5.0,
            threshold=8.0,
            word_count=2,
        )

        self.assertEqual(result.label, "test.label")
        self.assertEqual(result.text, "Test text")
        self.assertEqual(result.language, "en-us")
        self.assertTrue(result.passes)
        self.assertEqual(result.primary_score, 5.0)
        self.assertEqual(result.threshold, 8.0)
        self.assertEqual(result.word_count, 2)
