"""Top-level conversational AI assistant service interface."""

from __future__ import annotations

import uuid
from typing import Any

from app.ai.conversation.memory import ConversationMemory
from app.ai.conversation.orchestrator import ConversationalOrchestrator
from app.ai.conversation.schemas import AssistantResponse, ChatRequestPayload


class OpportunityAssistant:
    """Production-grade Grounded AI Opportunity Assistant entry point."""

    def __init__(
        self,
        orchestrator: ConversationalOrchestrator | None = None,
        memory: ConversationMemory | None = None,
        candidate_catalog: list[Any] | None = None,
    ) -> None:
        self.orchestrator = orchestrator or ConversationalOrchestrator(
            candidate_catalog=candidate_catalog
        )
        self.memory = memory or ConversationMemory()

    async def chat(
        self,
        payload: ChatRequestPayload,
        profile: Any | None = None,
    ) -> AssistantResponse:
        """Processes a user conversational turn, updating session state and returning
        a verified response.
        """
        conv_id = payload.conversation_id or str(uuid.uuid4())
        user_id = str(payload.user_id) if payload.user_id else None

        # Retrieve or initialize conversation context
        context = self.memory.get_or_create_context(
            conversation_id=conv_id,
            user_id=user_id,
        )

        # Apply any overrides from payload
        if payload.context_override:
            for k, v in payload.context_override.items():
                if hasattr(context, k):
                    setattr(context, k, v)

        # Execute conversation turn through the 8-stage orchestrator
        response = await self.orchestrator.handle_turn(
            message=payload.message,
            context=context,
            profile=profile,
            page=payload.page,
            page_size=payload.page_size,
        )

        return response
