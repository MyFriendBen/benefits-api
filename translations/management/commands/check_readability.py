"""
Django management command to check readability of translations.

This command analyzes translation text using various readability metrics:
- For English: Flesch-Kincaid Grade Level, Flesch Reading Ease, SMOG Index
- For Spanish: Fernández-Huerta, Szigriszt-Pazos, Crawford

Usage:
    python manage.py check_readability
    python manage.py check_readability --language en --whitelabel colorado
    python manage.py check_readability --language es --threshold 60
    python manage.py check_readability --fail-on-error
"""

import textstat
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from translations.models import Translation
from programs.models import Program
from screener.models import WhiteLabel


@dataclass
class ReadabilityResult:
    """Stores the result of a readability analysis for a single text."""
    label: str
    text: str
    language: str
    scores: Dict[str, float]
    passes: bool
    primary_score: float
    threshold: float
    word_count: int


class ReadabilityChecker:
    """
    Analyzes text readability using various metrics.
    
    For English text, we use Flesch-Kincaid Grade Level where lower is better
    (target: 8th grade or below for accessibility).
    
    For Spanish text, we use Fernández-Huerta score where higher is better
    (target: 60+ for good readability).
    """
    
    # Default thresholds
    ENGLISH_THRESHOLD = 8.0   # Maximum grade level (8th grade)
    SPANISH_THRESHOLD = 60.0  # Minimum Fernández-Huerta score
    
    # Minimum word count for meaningful analysis
    MIN_WORD_COUNT = 10
    
    def __init__(self, en_threshold: Optional[float] = None, es_threshold: Optional[float] = None):
        self.en_threshold = en_threshold if en_threshold is not None else self.ENGLISH_THRESHOLD
        self.es_threshold = es_threshold if es_threshold is not None else self.SPANISH_THRESHOLD
    
    def analyze_english(self, text: str) -> Dict[str, float]:
        """Analyze English text using multiple readability metrics."""
        textstat.set_lang('en')
        return {
            'flesch_reading_ease': textstat.flesch_reading_ease(text),
            'flesch_kincaid_grade': textstat.flesch_kincaid_grade(text),
            'smog_index': textstat.smog_index(text),
            'automated_readability_index': textstat.automated_readability_index(text),
            'coleman_liau_index': textstat.coleman_liau_index(text),
            'gunning_fog': textstat.gunning_fog(text),
        }
    
    def analyze_spanish(self, text: str) -> Dict[str, float]:
        """Analyze Spanish text using Spanish-specific readability metrics."""
        textstat.set_lang('es')
        return {
            'fernandez_huerta': textstat.fernandez_huerta(text),
            'szigriszt_pazos': textstat.szigriszt_pazos(text),
            'crawford': textstat.crawford(text),
        }
    
    def get_word_count(self, text: str) -> int:
        """Count words in text."""
        if not text:
            return 0
        return len(text.split())
    
    def check(self, label: str, text: str, lang: str) -> ReadabilityResult:
        """
        Check readability of a single text.
        
        Args:
            label: Translation label/key
            text: The text to analyze
            lang: Language code (e.g., 'en-us', 'es')
        
        Returns:
            ReadabilityResult with scores and pass/fail status
        """
        word_count = self.get_word_count(text)
        
        # Skip analysis for very short texts
        if not text or word_count < self.MIN_WORD_COUNT:
            return ReadabilityResult(
                label=label,
                text=text or "",
                language=lang,
                scores={},
                passes=True,  # Short texts pass by default
                primary_score=0,
                threshold=0,
                word_count=word_count
            )
        
        # Analyze based on language
        if lang.startswith('es'):
            scores = self.analyze_spanish(text)
            primary_score = scores['fernandez_huerta']
            passes = primary_score >= self.es_threshold
            threshold = self.es_threshold
        else:
            scores = self.analyze_english(text)
            primary_score = scores['flesch_kincaid_grade']
            passes = primary_score <= self.en_threshold
            threshold = self.en_threshold
        
        return ReadabilityResult(
            label=label,
            text=text,
            language=lang,
            scores=scores,
            passes=passes,
            primary_score=primary_score,
            threshold=threshold,
            word_count=word_count
        )


class Command(BaseCommand):
    help = 'Check readability of translations to ensure content accessibility'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--language', '-l',
            type=str,
            default='en-us',
            help='Language code to check (default: en-us). Options: en-us, es, vi'
        )
        parser.add_argument(
            '--whitelabel', '-w',
            type=str,
            help='White label code to filter by (e.g., "colorado", "co")'
        )
        parser.add_argument(
            '--threshold', '-t',
            type=float,
            help='Custom threshold (grade level for English, Fernández-Huerta score for Spanish)'
        )
        parser.add_argument(
            '--fail-on-error',
            action='store_true',
            help='Exit with error code if any translations fail readability check'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed scores for all translations'
        )
        parser.add_argument(
            '--min-words',
            type=int,
            default=10,
            help='Minimum word count for analysis (default: 10)'
        )
        parser.add_argument(
            '--label-filter',
            type=str,
            help='Filter translations by label prefix (e.g., "program.")'
        )
        parser.add_argument(
            '--show-passing',
            action='store_true',
            help='Also show passing translations in output'
        )
    
    def handle(self, *args, **options):
        language = options['language']
        whitelabel = options.get('whitelabel')
        threshold = options['threshold']
        fail_on_error = options['fail_on_error']
        detailed = options['detailed']
        min_words = options['min_words']
        label_filter = options.get('label_filter')
        show_passing = options['show_passing']
        
        # Set up the checker
        checker = ReadabilityChecker(
            en_threshold=threshold if language.startswith('en') else None,
            es_threshold=threshold if language.startswith('es') else None
        )
        checker.MIN_WORD_COUNT = min_words
        
        # Fetch translations
        self.stdout.write(f'\nFetching translations for language: {language}')
        
        translations = Translation.objects.filter(active=True).prefetch_related('translations')
        
        # Filter by white label if specified
        allowed_labels: Optional[Set[str]] = None
        if whitelabel:
            allowed_labels = self._get_whitelabel_translation_labels(whitelabel)
            if not allowed_labels:
                raise CommandError(f'No programs found for white label: {whitelabel}')
            self.stdout.write(f'Filtering by white label: {whitelabel} ({len(allowed_labels)} translation labels)')
        
        if label_filter:
            translations = translations.filter(label__startswith=label_filter)
        
        self.stdout.write(f'Found {translations.count()} active translations\n')
        
        # Analyze each translation
        passing_results: List[ReadabilityResult] = []
        failing_results: List[ReadabilityResult] = []
        skipped_count = 0
        
        for translation in translations:
            # Skip if not in allowed labels (when filtering by whitelabel)
            if allowed_labels is not None and translation.label not in allowed_labels:
                continue
                
            translation.set_current_language(language)
            text = translation.text
            
            if not text:
                skipped_count += 1
                continue
            
            result = checker.check(translation.label, text, language)
            
            if result.word_count < min_words:
                skipped_count += 1
                continue
            
            if result.passes:
                passing_results.append(result)
            else:
                failing_results.append(result)
        
        # Print summary
        self._print_summary(
            passing_results,
            failing_results,
            skipped_count,
            language,
            checker,
            detailed,
            show_passing,
            whitelabel
        )
        
        # Exit with error if requested and there are failures
        if fail_on_error and failing_results:
            raise CommandError(
                f'{len(failing_results)} translation(s) failed readability check'
            )
    
    def _get_whitelabel_translation_labels(self, whitelabel_code: str) -> Set[str]:
        """
        Get all translation labels associated with programs for a specific white label.
        
        Returns a set of translation labels that belong to programs in the white label.
        """
        # Try to find white label by code or name
        try:
            wl = WhiteLabel.objects.get(code__iexact=whitelabel_code)
        except WhiteLabel.DoesNotExist:
            try:
                wl = WhiteLabel.objects.get(name__iexact=whitelabel_code)
            except WhiteLabel.DoesNotExist:
                return set()
        
        # Get all programs for this white label
        programs = Program.objects.filter(white_label=wl)
        
        # Collect translation labels from programs
        labels: Set[str] = set()
        translation_fields = [
            'name', 'name_short', 'description', 'description_short',
            'learn_more_link', 'apply_button_link', 'apply_button_description',
            'value_description', 'estimated_delivery_time', 'estimated_application_time',
            'category'
        ]
        
        for program in programs:
            for field in translation_fields:
                translation = getattr(program, field, None)
                if translation and hasattr(translation, 'label'):
                    labels.add(translation.label)
        
        return labels
    
    def _print_summary(
        self,
        passing: List[ReadabilityResult],
        failing: List[ReadabilityResult],
        skipped: int,
        language: str,
        checker: ReadabilityChecker,
        detailed: bool,
        show_passing: bool,
        whitelabel: Optional[str] = None
    ):
        """Print a formatted summary of the readability analysis."""
        total = len(passing) + len(failing)
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('READABILITY ANALYSIS REPORT')
        self.stdout.write('=' * 60)
        
        self.stdout.write(f'\nLanguage: {language}')
        if whitelabel:
            self.stdout.write(f'White Label: {whitelabel}')
        
        if language.startswith('es'):
            self.stdout.write(f'Metric: Fernández-Huerta (higher is better)')
            self.stdout.write(f'Threshold: >= {checker.es_threshold}')
        else:
            self.stdout.write(f'Metric: Flesch-Kincaid Grade Level (lower is better)')
            self.stdout.write(f'Threshold: <= {checker.en_threshold} (8th grade)')
        
        self.stdout.write(f'\nTotal analyzed: {total}')
        self.stdout.write(f'Skipped (too short): {skipped}')
        self.stdout.write(
            self.style.SUCCESS(f'✅ Passing: {len(passing)} ({100 * len(passing) / total:.1f}%)') if total > 0 else 'Passing: 0'
        )
        self.stdout.write(
            self.style.ERROR(f'❌ Failing: {len(failing)} ({100 * len(failing) / total:.1f}%)') if failing else self.style.SUCCESS('✅ Failing: 0')
        )
        
        # Show passing results if requested
        if show_passing and passing:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write(self.style.SUCCESS('PASSING TRANSLATIONS:'))
            self.stdout.write('-' * 60)
            
            for result in sorted(passing, key=lambda r: r.primary_score):
                self._print_result(result, detailed, is_failing=False)
        elif passing and not show_passing:
            self.stdout.write(self.style.NOTICE(f'\n💡 Tip: Use --show-passing to see the {len(passing)} passing translations'))
        
        # Show failing results
        if failing:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write(self.style.ERROR('FAILING TRANSLATIONS:'))
            self.stdout.write('-' * 60)
            
            # Sort by score (worst first for English, best first for Spanish)
            if language.startswith('es'):
                failing_sorted = sorted(failing, key=lambda r: r.primary_score)
            else:
                failing_sorted = sorted(failing, key=lambda r: -r.primary_score)
            
            for result in failing_sorted:
                self._print_result(result, detailed, is_failing=True)
        
        self.stdout.write('\n' + '=' * 60 + '\n')
    
    def _print_result(self, result: ReadabilityResult, detailed: bool, is_failing: bool):
        """Print details for a single translation result."""
        style = self.style.ERROR if is_failing else self.style.SUCCESS
        icon = '❌' if is_failing else '✅'
        
        self.stdout.write(f'\n{icon} {result.label}')
        self.stdout.write(f'   Score: {result.primary_score:.1f} (threshold: {result.threshold})')
        self.stdout.write(f'   Words: {result.word_count}')
        
        # Truncate text for display
        display_text = result.text[:100] + '...' if len(result.text) > 100 else result.text
        display_text = display_text.replace('\n', ' ')
        self.stdout.write(f'   Text: "{display_text}"')
        
        if detailed:
            self.stdout.write('   All scores:')
            for metric, score in result.scores.items():
                self.stdout.write(f'      {metric}: {score:.2f}')
