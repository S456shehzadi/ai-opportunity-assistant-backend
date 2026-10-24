"""Conversation memory manager maintaining state and resolving contextual follow-ups."""

from __future__ import annotations

import re
import threading

from app.ai.conversation.context import ConversationContext
from app.opportunities.ranking.factors import get_opp_org, get_opp_title


class ConversationMemory:
    """Thread-safe state store managing multi-turn conversation contexts."""

    _sessions: dict[str, ConversationContext] = {}
    _lock = threading.Lock()

    @classmethod
    def get_or_create(cls, conversation_id: str, user_id: str | None = None) -> ConversationContext:
        """Retrieves existing session context or initializes a fresh one."""
        with cls._lock:
            if conversation_id not in cls._sessions:
                cls._sessions[conversation_id] = ConversationContext(
                    conversation_id=conversation_id, user_id=user_id
                )
            ctx = cls._sessions[conversation_id]
            if user_id and not ctx.user_id:
                ctx.user_id = user_id
            return ctx

    @classmethod
    def update(cls, context: ConversationContext) -> None:
        """Persists updated context state back into session store."""
        with cls._lock:
            cls._sessions[context.conversation_id] = context

    @classmethod
    def clear(cls, conversation_id: str) -> None:
        """Removes a conversation context from memory."""
        with cls._lock:
            cls._sessions.pop(conversation_id, None)

    @classmethod
    def get_or_create_context(
        cls, conversation_id: str, user_id: str | None = None
    ) -> ConversationContext:
        """Alias for get_or_create."""
        return cls.get_or_create(conversation_id=conversation_id, user_id=user_id)

    @classmethod
    def resolve_references(cls, message: str, context: ConversationContext) -> list[str]:
        """Alias for resolve_contextual_references."""
        return cls.resolve_contextual_references(message=message, context=context)

    @classmethod
    def resolve_contextual_references(cls, message: str, context: ConversationContext) -> list[str]:
        """Resolves ordinal, pronoun, and organizational references to active candidate IDs."""
        if not context.active_opportunities:
            return []

        lower_msg = message.lower().strip()
        matched_ids: list[str] = []

        # 1. Collective references ("which of these", "compare them", "all of these", "both")
        if any(
            p in lower_msg
            for p in (
                "which of these",
                "which one",
                "these",
                "both",
                "all of them",
                "compare them",
                "any of these",
            )
        ):
            return [
                str(
                    (o.get("id") or o.get("canonical_key") or f"opp-{i}")
                    if isinstance(o, dict)
                    else (getattr(o, "id", None) or getattr(o, "canonical_key", f"opp-{i}"))
                )
                for i, o in enumerate(context.active_opportunities)
            ]

        # 2. Ordinal references ("first", "second", "third", "last")
        ordinal_map = {
            "first": 0,
            "1st": 0,
            "second": 1,
            "2nd": 1,
            "third": 2,
            "3rd": 2,
            "fourth": 3,
            "4th": 3,
            "last": len(context.active_opportunities) - 1,
        }
        for word, idx in ordinal_map.items():
            if re.search(r"\b" + re.escape(word) + r"\b", lower_msg):
                if 0 <= idx < len(context.active_opportunities):
                    opp = context.active_opportunities[idx]
                    if isinstance(opp, dict):
                        o_id = opp.get("id") or opp.get("canonical_key") or f"opp-{idx}"
                    else:
                        o_id = getattr(opp, "id", None) or getattr(
                            opp, "canonical_key", f"opp-{idx}"
                        )
                    matched_ids.append(str(o_id))

        if matched_ids:
            return list(dict.fromkeys(matched_ids))

        # 3. Organization or Title keyword match against active opportunities
        for idx, opp in enumerate(context.active_opportunities):
            title = get_opp_title(opp).lower()
            org = get_opp_org(opp).lower()

            org_tokens = [t for t in re.findall(r"\w+", org) if len(t) > 2]
            title_tokens = [
                t
                for t in re.findall(r"\w+", title)
                if len(t) > 3 and t not in ("scholarship", "master", "fellowship")
            ]

            if any(t in lower_msg for t in org_tokens) or any(t in lower_msg for t in title_tokens):
                if isinstance(opp, dict):
                    o_id = opp.get("id") or opp.get("canonical_key") or f"opp-{idx}"
                else:
                    o_id = getattr(opp, "id", None) or getattr(opp, "canonical_key", f"opp-{idx}")
                matched_ids.append(str(o_id))

        return list(dict.fromkeys(matched_ids))
