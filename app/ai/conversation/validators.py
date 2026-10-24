"""Response grounding validation and anti-hallucination verification."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from app.ai.conversation.schemas import (
    AssistantResponse,
    ClaimType,
    ResponseClaim,
)


class ResponseGroundingValidator:
    """Verifies that generated responses are strictly grounded in factual source records."""

    PROBABILITY_PATTERNS = [
        re.compile(
            r"\b(?:\d{1,3}%\s+(?:chance|probability|likelihood)\s+of\s+(?:admission|acceptance|getting))\b",
            re.I,
        ),
        re.compile(
            r"\b(?:chances?\s+of\s+(?:getting\s+in|acceptance|selection)\s+are\s+(?:high|low|medium|\d{1,3}%))\b",
            re.I,
        ),
        re.compile(r"\b(?:you\s+will\s+definitely\s+get\s+(?:in|accepted))\b", re.I),
        re.compile(r"\b(?:admission\s+rate\s+for\s+you)\b", re.I),
    ]

    GUESSED_URL_PATTERNS = [
        re.compile(r"https?://[^\s/]+/apply(?:-now)?/?(?!\S)", re.I),
        re.compile(r"https?://[^\s/]+/application/?(?!\S)", re.I),
    ]

    @classmethod
    def validate_and_filter(
        cls,
        response: AssistantResponse,
        verified_opportunities: list[Any],
        allowed_urls: set[str] | None = None,
    ) -> AssistantResponse:
        """Enforces zero-hallucination, zero outcome prediction, and verified URL rules."""
        msg = response.message
        claims: list[ResponseClaim] = []

        # 1. Enforce Zero Outcome Prediction
        for pat in cls.PROBABILITY_PATTERNS:
            if pat.search(msg):
                # Sanitize out prediction statements
                msg = pat.sub("[Outcome predictions are strictly prohibited]", msg)
                claims.append(
                    ResponseClaim(
                        claim_text="Outcome prediction detected and disarmed.",
                        claim_type=ClaimType.ELIGIBILITY,
                        supported=False,
                        rejection_reason=(
                            "Strict guardrail: Zero outcome prediction policy violation."
                        ),
                    )
                )

        # 2. Extract Allowed URLs
        valid_urls = set(allowed_urls or set())
        for opp in verified_opportunities:
            for field in ("official_source_url", "source_url", "application_url"):
                val = getattr(opp, field, None) or (
                    opp.get(field) if isinstance(opp, dict) else None
                )
                if val:
                    valid_urls.add(str(val))
                    # Also allow stripped trailing slash
                    valid_urls.add(str(val).rstrip("/"))

        for cit in response.citations:
            if cit.url:
                valid_urls.add(str(cit.url))
                valid_urls.add(str(cit.url).rstrip("/"))

        # 3. Detect and neutralize ungrounded/guessed URLs
        found_urls = re.findall(r"https?://[^\s)\]]+", msg)
        for u in found_urls:
            cleaned_url = u.rstrip(".,;:!?'\"")
            if cleaned_url not in valid_urls:
                # Check if it was a guessed /apply path
                is_guessed = any(p.search(cleaned_url) for p in cls.GUESSED_URL_PATTERNS)
                if is_guessed or not cls._is_whitelisted_domain(cleaned_url, valid_urls):
                    msg = msg.replace(u, "[Unverified URL removed]")
                    claims.append(
                        ResponseClaim(
                            claim_text=f"Removed guessed URL: {cleaned_url}",
                            claim_type=ClaimType.APPLICATION,
                            supported=False,
                            rejection_reason=(
                                "Ungrounded URL not present in verified source records."
                            ),
                        )
                    )

        # 4. Generate positive claim verification records
        for opp in verified_opportunities:
            title = getattr(opp, "title", None) or (
                opp.get("title") if isinstance(opp, dict) else None
            )
            if title and title in msg:
                claims.append(
                    ResponseClaim(
                        claim_text=f"Referenced verified opportunity: {title}",
                        claim_type=ClaimType.TITLE,
                        source_ids=[
                            str(
                                getattr(opp, "id", None)
                                or (opp.get("id") if isinstance(opp, dict) else "")
                            )
                        ],
                        supported=True,
                    )
                )

        response.message = msg
        response.claims_verified = claims
        return response

    @classmethod
    def _is_whitelisted_domain(cls, url: str, valid_urls: set[str]) -> bool:
        """Checks if URL domain matches any verified source domain."""
        try:
            target_domain = urlparse(url).netloc.lower()
            for v in valid_urls:
                v_domain = urlparse(v).netloc.lower()
                if target_domain and target_domain == v_domain:
                    return True
        except Exception:
            pass
        return False
