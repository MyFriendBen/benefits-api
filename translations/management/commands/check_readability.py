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
    python manage.py check_readability --language es --whitelabel co --output report.json
    python manage.py check_readability --language es --whitelabel co --output report.csv
"""

import csv
import json
import textstat
from dataclasses import dataclass, asdict
from pathlib import Path
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
    ENGLISH_THRESHOLD = 8.0  # Maximum grade level (8th grade)
    SPANISH_THRESHOLD = 60.0  # Minimum Fernández-Huerta score

    # Minimum word count for meaningful analysis
    DEFAULT_MIN_WORD_COUNT = 10

    def __init__(
        self,
        en_threshold: Optional[float] = None,
        es_threshold: Optional[float] = None,
        min_words: Optional[int] = None,
    ):
        self.en_threshold = en_threshold if en_threshold is not None else self.ENGLISH_THRESHOLD
        self.es_threshold = es_threshold if es_threshold is not None else self.SPANISH_THRESHOLD
        self.min_word_count = min_words if min_words is not None else self.DEFAULT_MIN_WORD_COUNT

    def analyze_english(self, text: str) -> Dict[str, float]:
        """Analyze English text using multiple readability metrics."""
        textstat.set_lang("en")
        return {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
            "smog_index": textstat.smog_index(text),
            "automated_readability_index": textstat.automated_readability_index(text),
            "coleman_liau_index": textstat.coleman_liau_index(text),
            "gunning_fog": textstat.gunning_fog(text),
        }

    def analyze_spanish(self, text: str) -> Dict[str, float]:
        """Analyze Spanish text using Spanish-specific readability metrics."""
        textstat.set_lang("es")
        return {
            "fernandez_huerta": textstat.fernandez_huerta(text),
            "szigriszt_pazos": textstat.szigriszt_pazos(text),
            "crawford": textstat.crawford(text),
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
        if not text or word_count < self.min_word_count:
            return ReadabilityResult(
                label=label,
                text=text or "",
                language=lang,
                scores={},
                passes=True,  # Short texts pass by default
                primary_score=0,
                threshold=0,
                word_count=word_count,
            )

        # Analyze based on language
        if lang.startswith("es"):
            scores = self.analyze_spanish(text)
            primary_score = scores["fernandez_huerta"]
            passes = primary_score >= self.es_threshold
            threshold = self.es_threshold
        else:
            scores = self.analyze_english(text)
            primary_score = scores["flesch_kincaid_grade"]
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
            word_count=word_count,
        )


class Command(BaseCommand):
    help = "Check readability of translations to ensure content accessibility"

    def add_arguments(self, parser):
        parser.add_argument(
            "--language",
            "-l",
            type=str,
            default="en-us",
            help="Language code to check (default: en-us). Options: en-us, es, etc.",
        )
        parser.add_argument(
            "--whitelabel", "-w", type=str, help='White label code to filter by (e.g., "colorado", "co")'
        )
        parser.add_argument(
            "--threshold",
            "-t",
            type=float,
            help="Custom threshold (grade level for English, Fernández-Huerta score for Spanish)",
        )
        parser.add_argument(
            "--fail-on-error",
            action="store_true",
            help="Exit with error code if any translations fail readability check",
        )
        parser.add_argument("--detailed", action="store_true", help="Show detailed scores for all translations")
        parser.add_argument("--min-words", type=int, default=10, help="Minimum word count for analysis (default: 10)")
        parser.add_argument("--label-filter", type=str, help='Filter translations by label prefix (e.g., "program.")')
        parser.add_argument("--show-passing", action="store_true", help="Also show passing translations in output")
        parser.add_argument(
            "--output",
            "-o",
            type=str,
            help="Output file path (e.g., report.txt, report.json, report.csv)",
        )
        parser.add_argument(
            "--format",
            "-f",
            type=str,
            choices=["text", "json", "csv"],
            help="Output format (default: auto-detected from file extension, or text)",
        )

    def handle(self, *args, **options):
        language = options["language"]
        whitelabel = options.get("whitelabel")

        checker = self._build_checker(language, options["threshold"], options["min_words"])
        translations = self._fetch_translations(language, whitelabel, options.get("label_filter"))
        passing, failing, skipped = self._analyze(translations, language, checker, options["min_words"])

        self._print_summary(passing, failing, skipped, language, checker, options["detailed"], options["show_passing"], whitelabel)

        output_file, output_format = self._resolve_output_path(options.get("output"), options.get("format"), language, whitelabel)
        self._export_report(output_file, output_format, passing, failing, skipped, language, checker, whitelabel)

        if options["fail_on_error"] and failing:
            raise CommandError(f"{len(failing)} translation(s) failed readability check")

    def _build_checker(self, language: str, threshold: Optional[float], min_words: int) -> ReadabilityChecker:
        return ReadabilityChecker(
            en_threshold=threshold if language.startswith("en") else None,
            es_threshold=threshold if language.startswith("es") else None,
            min_words=min_words,
        )

    def _fetch_translations(self, language: str, whitelabel: Optional[str], label_filter: Optional[str]):
        self.stdout.write(f"\nFetching translations for language: {language}")
        translations = Translation.objects.filter(active=True).prefetch_related("translations")

        if whitelabel:
            allowed_labels = self._get_whitelabel_translation_labels(whitelabel)
            if not allowed_labels:
                raise CommandError(f"No programs found for white label: {whitelabel}")
            translations = translations.filter(label__in=allowed_labels)
            self.stdout.write(f"Filtering by white label: {whitelabel} ({len(allowed_labels)} translation labels)")

        if label_filter:
            translations = translations.filter(label__startswith=label_filter)

        self.stdout.write(f"Found {translations.count()} active translations\n")
        return translations

    def _analyze(self, translations, language: str, checker: ReadabilityChecker, min_words: int):
        passing: List[ReadabilityResult] = []
        failing: List[ReadabilityResult] = []
        skipped = 0

        for translation in translations:
            translation.set_current_language(language)
            text = translation.text

            if not text:
                skipped += 1
                continue

            result = checker.check(translation.label, text, language)

            if result.word_count < min_words:
                skipped += 1
                continue

            if result.passes:
                passing.append(result)
            else:
                failing.append(result)

        return passing, failing, skipped

    def _resolve_output_path(
        self,
        output_file: Optional[str],
        output_format: Optional[str],
        language: str,
        whitelabel: Optional[str],
    ) -> tuple[str, str]:
        """Return (resolved_path, resolved_format), creating the output directory as needed."""
        if output_file and not output_format:
            ext = Path(output_file).suffix.lower()
            output_format = {".json": "json", ".csv": "csv"}.get(ext, "text")

        if not output_file:
            suffix = {"json": ".json", "csv": ".csv"}.get(output_format or "", ".txt")
            name = f"readability-check-{language}"
            if whitelabel:
                name += f"-{whitelabel}"
            output_file = name + suffix

        p = Path(output_file)
        if p.parent == Path("."):
            p = Path("readability-output") / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p), output_format or "text"

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

        translation_fields = [
            "name",
            "description",
            "description_short",
            "learn_more_link",
            "apply_button_link",
            "apply_button_description",
            "value_type",
            "estimated_delivery_time",
            "estimated_application_time",
            "estimated_value",
            "website_description",
        ]
        programs = Program.objects.filter(white_label=wl).select_related(*translation_fields)
        labels: Set[str] = set()

        for program in programs:
            for field in translation_fields:
                translation = getattr(program, field, None)
                if translation and hasattr(translation, "label"):
                    labels.add(translation.label)

        return labels

    def _export_report(
        self,
        output_file: str,
        output_format: str,
        passing: List[ReadabilityResult],
        failing: List[ReadabilityResult],
        skipped: int,
        language: str,
        checker: ReadabilityChecker,
        whitelabel: Optional[str] = None,
    ):
        """Export the readability report to a file."""
        if output_format == "json":
            self._export_json(output_file, passing, failing, skipped, language, checker, whitelabel)
        elif output_format == "csv":
            self._export_csv(output_file, passing, failing)
        else:
            self._export_text(output_file, passing, failing, skipped, language, checker, whitelabel)

        self.stdout.write(self.style.SUCCESS(f"\n📄 Report saved to: {output_file}"))

    def _export_json(
        self,
        output_file: str,
        passing: List[ReadabilityResult],
        failing: List[ReadabilityResult],
        skipped: int,
        language: str,
        checker: ReadabilityChecker,
        whitelabel: Optional[str] = None,
    ):
        """Export report as JSON."""
        total = len(passing) + len(failing)

        report = {
            "summary": {
                "language": language,
                "whitelabel": whitelabel,
                "threshold": checker.es_threshold if language.startswith("es") else checker.en_threshold,
                "metric": "fernandez_huerta" if language.startswith("es") else "flesch_kincaid_grade",
                "total_analyzed": total,
                "skipped": skipped,
                "passing_count": len(passing),
                "failing_count": len(failing),
                "passing_percentage": round(100 * len(passing) / total, 1) if total > 0 else 0,
            },
            "failing": [
                {
                    "label": r.label,
                    "score": round(r.primary_score, 1),
                    "threshold": r.threshold,
                    "word_count": r.word_count,
                    "text": r.text[:200] + "..." if len(r.text) > 200 else r.text,
                    "all_scores": {k: round(v, 2) for k, v in r.scores.items()},
                }
                for r in sorted(failing, key=lambda x: x.primary_score)
            ],
            "passing": [
                {
                    "label": r.label,
                    "score": round(r.primary_score, 1),
                    "word_count": r.word_count,
                }
                for r in sorted(passing, key=lambda x: x.primary_score, reverse=language.startswith("es"))
            ],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    def _export_csv(
        self,
        output_file: str,
        passing: List[ReadabilityResult],
        failing: List[ReadabilityResult],
    ):
        """Export report as CSV."""
        all_results = [(r, "FAIL") for r in failing] + [(r, "PASS") for r in passing]

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Status", "Label", "Score", "Threshold", "Word Count", "Text Preview"])

            for result, status in sorted(all_results, key=lambda x: (x[1], x[0].label)):
                text_preview = result.text[:100].replace("\n", " ") if result.text else ""
                writer.writerow(
                    [
                        status,
                        result.label,
                        round(result.primary_score, 1),
                        result.threshold,
                        result.word_count,
                        text_preview,
                    ]
                )

    def _build_report_lines(
        self,
        passing: List[ReadabilityResult],
        failing: List[ReadabilityResult],
        skipped: int,
        language: str,
        checker: ReadabilityChecker,
        whitelabel: Optional[str] = None,
        show_passing: bool = True,
        detailed: bool = False,
    ) -> List[str]:
        """Build the report as a list of plain-text lines.

        Used by both _export_text (writes to file) and _print_summary (writes to stdout).
        """
        total = len(passing) + len(failing)

        lines = [
            "=" * 60,
            "READABILITY ANALYSIS REPORT",
            "=" * 60,
            "",
            f"Language: {language}",
        ]

        if whitelabel:
            lines.append(f"White Label: {whitelabel}")

        if language.startswith("es"):
            lines.append("Metric: Fernández-Huerta (higher is better)")
            lines.append(f"Threshold: >= {checker.es_threshold}")
        else:
            lines.append("Metric: Flesch-Kincaid Grade Level (lower is better)")
            lines.append(f"Threshold: <= {checker.en_threshold}")

        lines.extend([
            "",
            f"Total analyzed: {total}",
            f"Skipped (too short): {skipped}",
            f"✅ Passing: {len(passing)} ({100 * len(passing) / total:.1f}%)" if total > 0 else "✅ Passing: 0",
            f"❌ Failing: {len(failing)} ({100 * len(failing) / total:.1f}%)" if failing else "✅ Failing: 0",
        ])

        if failing:
            lines.extend(["", "-" * 60, "FAILING TRANSLATIONS:", "-" * 60])
            # Sort worst-first: highest score for English (lower is better), lowest for Spanish
            failing_sorted = sorted(failing, key=lambda r: r.primary_score, reverse=not language.startswith("es"))
            for result in failing_sorted:
                display_text = result.text[:100].replace("\n", " ") + ("..." if len(result.text) > 100 else "")
                lines.extend([
                    "",
                    f"❌ {result.label}",
                    f"   Score: {result.primary_score:.1f} (threshold: {result.threshold})",
                    f"   Words: {result.word_count}",
                    f'   Text: "{display_text}"',
                ])
                if detailed:
                    lines.append("   All scores:")
                    lines.extend([f"      {m}: {s:.2f}" for m, s in result.scores.items()])

        if show_passing and passing:
            lines.extend(["", "-" * 60, "PASSING TRANSLATIONS:", "-" * 60])
            for result in sorted(passing, key=lambda r: r.primary_score, reverse=language.startswith("es")):
                lines.extend([
                    "",
                    f"✅ {result.label}",
                    f"   Score: {result.primary_score:.1f}",
                    f"   Words: {result.word_count}",
                ])
                if detailed:
                    lines.append("   All scores:")
                    lines.extend([f"      {m}: {s:.2f}" for m, s in result.scores.items()])

        lines.append("\n" + "=" * 60)
        return lines

    def _export_text(
        self,
        output_file: str,
        passing: List[ReadabilityResult],
        failing: List[ReadabilityResult],
        skipped: int,
        language: str,
        checker: ReadabilityChecker,
        whitelabel: Optional[str] = None,
    ):
        """Export report as plain text."""
        lines = self._build_report_lines(passing, failing, skipped, language, checker, whitelabel, show_passing=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _print_summary(
        self,
        passing: List[ReadabilityResult],
        failing: List[ReadabilityResult],
        skipped: int,
        language: str,
        checker: ReadabilityChecker,
        detailed: bool,
        show_passing: bool,
        whitelabel: Optional[str] = None,
    ):
        """Print a formatted summary of the readability analysis."""
        lines = self._build_report_lines(
            passing, failing, skipped, language, checker, whitelabel,
            show_passing=show_passing, detailed=detailed,
        )
        for line in lines:
            if line.startswith("✅"):
                self.stdout.write(self.style.SUCCESS(line))
            elif line.startswith("❌"):
                self.stdout.write(self.style.ERROR(line))
            elif line == "PASSING TRANSLATIONS:":
                self.stdout.write(self.style.SUCCESS(line))
            elif line == "FAILING TRANSLATIONS:":
                self.stdout.write(self.style.ERROR(line))
            else:
                self.stdout.write(line)

        if passing and not show_passing:
            self.stdout.write(
                self.style.NOTICE(f"\n💡 Tip: Use --show-passing to see the {len(passing)} passing translations")
            )
