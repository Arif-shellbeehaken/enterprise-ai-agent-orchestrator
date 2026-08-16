"""
PII Sanitizer using Microsoft Presidio.
All user inputs and tool outputs must be redacted before LLM dispatch.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional Presidio imports – graceful degradation if not installed / models missing
try:
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.warning("Presidio not available – using regex fallback sanitizer")


class PIISanitizer:
    """
    Asynchronous-friendly PII redactor.
    Returns (sanitized_text, mapping) where mapping maps placeholder tokens
    back to original values for post-processing if needed.
    """

    def __init__(
        self,
        language: str = "en",
        entities: Optional[List[str]] = None,
    ):
        self.language = language
        self.entities = entities or [
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "US_SSN",
            "PERSON",
            "API_KEY",
        ]
        self._analyzer: Any = None
        self._anonymizer: Any = None
        self._token_counter = 0

        if PRESIDIO_AVAILABLE:
            self._init_presidio()

    def _init_presidio(self) -> None:
        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()

        # Custom recognizer for generic API keys / secrets
        api_key_pattern = Pattern(
            name="api_key_pattern",
            regex=r"(?i)(?:api[_-]?key|secret|token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
            score=0.7,
        )
        api_key_recognizer = PatternRecognizer(
            supported_entity="API_KEY",
            patterns=[api_key_pattern],
        )
        self._analyzer.registry.add_recognizer(api_key_recognizer)

    def _regex_fallback(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Simple regex-based redaction when Presidio is unavailable."""
        mapping: Dict[str, str] = {}
        patterns = [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL"),
            (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "PHONE"),
            (r"\b(?:\d[ -]*?){13,19}\b", "CREDIT_CARD"),
            (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
            (
                r"(?i)(?:api[_-]?key|secret|token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
                "API_KEY",
            ),
        ]

        sanitized = text
        for pattern, label in patterns:
            def replacer(match: re.Match, lbl=label) -> str:
                self._token_counter += 1
                token = f"<{lbl}_{self._token_counter}>"
                mapping[token] = match.group(0)
                return token

            sanitized = re.sub(pattern, replacer, sanitized)
        return sanitized, mapping

    def sanitize_text(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Sanitize PII from text.
        Returns:
            sanitized_text: redacted string
            mapping: dict of {placeholder: original_value}
        """
        if not text or not text.strip():
            return text, {}

        if not PRESIDIO_AVAILABLE or self._analyzer is None:
            return self._regex_fallback(text)

        try:
            results = self._analyzer.analyze(
                text=text,
                language=self.language,
                entities=self.entities,
            )
            if not results:
                return text, {}

            anonymized = self._anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
                    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
                    "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
                    "CREDIT_CARD": OperatorConfig("replace", {"new_value": "<CARD>"}),
                    "US_SSN": OperatorConfig("replace", {"new_value": "<SSN>"}),
                    "PERSON": OperatorConfig("replace", {"new_value": "<PERSON>"}),
                    "API_KEY": OperatorConfig("replace", {"new_value": "<API_KEY>"}),
                },
            )

            # Build simple mapping from original spans
            mapping: Dict[str, str] = {}
            for r in results:
                original = text[r.start : r.end]
                placeholder = f"<{r.entity_type}>"
                mapping[placeholder] = original

            return anonymized.text, mapping
        except Exception as exc:
            logger.exception("Presidio sanitization failed, falling back to regex: %s", exc)
            return self._regex_fallback(text)

    async def asanitize_text(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Async wrapper (Presidio itself is sync; run in threadpool if needed)."""
        return self.sanitize_text(text)


# Singleton for convenience
_default_sanitizer: Optional[PIISanitizer] = None


def get_pii_sanitizer() -> PIISanitizer:
    global _default_sanitizer
    if _default_sanitizer is None:
        from app.core.config import settings

        _default_sanitizer = PIISanitizer(
            language=settings.PII_LANGUAGE,
            entities=settings.PII_ENTITIES,
        )
    return _default_sanitizer
