"""Content quality assessment evaluating text density, structure, and readability."""

from app.web.models.document import ContentQualityScore, ExtractedHeading


class ContentQualityAnalyzer:
    """Evaluates content completeness, structural hierarchy, and signal-to-noise ratio."""

    @classmethod
    def analyze(
        cls,
        clean_text: str,
        raw_html: str,
        headings: list[ExtractedHeading],
        word_count: int,
    ) -> ContentQualityScore:
        """Computes structural metrics and heuristic quality score for a document."""
        text_length = len(clean_text)
        html_length = len(raw_html)

        text_to_code = round(text_length / max(1, html_length), 4)
        has_main_content = word_count >= 50

        flags: list[str] = []
        score = 0.5  # Neutral baseline

        # Word count contribution
        if word_count < 30:
            flags.append("very_short_text")
            score -= 0.3
        elif word_count >= 150:
            flags.append("substantial_content")
            score += 0.2
        elif word_count >= 80:
            score += 0.1

        # Text-to-code ratio contribution
        if text_to_code < 0.05:
            flags.append("low_text_to_code_ratio")
            score -= 0.1
        elif text_to_code > 0.20:
            score += 0.15

        # Headings structure contribution
        if not headings:
            flags.append("no_headings")
            score -= 0.1
        elif len(headings) >= 2:
            flags.append("structured_headings")
            score += 0.15

        quality_score = max(0.0, min(1.0, round(score, 2)))

        return ContentQualityScore(
            text_length=text_length,
            word_count=word_count,
            text_to_code_ratio=text_to_code,
            has_main_content=has_main_content,
            quality_score=quality_score,
            quality_flags=flags,
        )
