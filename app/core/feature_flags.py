"""Centralized feature flag service supporting remote configuration and safe rollouts."""

from __future__ import annotations

import logging
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FeatureFlagKey(StrEnum):
    """Enumeration of system and beta feature flags."""

    LIVE_WEB_SEARCH = "live_web_search"
    SEMANTIC_DISCOVERY = "semantic_discovery"
    AI_CONVERSATIONAL_CHAT = "ai_conversational_chat"
    OPPORTUNITY_MONITORING = "opportunity_monitoring"
    PUSH_NOTIFICATIONS = "push_notifications"
    BETA_FEEDBACK_WIDGET = "beta_feedback_widget"
    EXPERIMENTAL_MULTILINGUAL = "experimental_multilingual"
    APPLICATION_EXPORT = "application_export"


class FeatureFlagState(BaseModel):
    """Metadata and current runtime state of a feature flag."""

    key: FeatureFlagKey
    enabled: bool
    description: str
    beta_only: bool = False
    rollout_percentage: int = Field(default=100, ge=0, le=100)


DEFAULT_FEATURE_FLAGS: dict[FeatureFlagKey, FeatureFlagState] = {
    FeatureFlagKey.LIVE_WEB_SEARCH: FeatureFlagState(
        key=FeatureFlagKey.LIVE_WEB_SEARCH,
        enabled=True,
        description="Enables live Tavily/SearXNG web search for discovery",
        beta_only=False,
        rollout_percentage=100,
    ),
    FeatureFlagKey.SEMANTIC_DISCOVERY: FeatureFlagState(
        key=FeatureFlagKey.SEMANTIC_DISCOVERY,
        enabled=True,
        description="Enables dense vector embeddings and hybrid reranking",
        beta_only=False,
        rollout_percentage=100,
    ),
    FeatureFlagKey.AI_CONVERSATIONAL_CHAT: FeatureFlagState(
        key=FeatureFlagKey.AI_CONVERSATIONAL_CHAT,
        enabled=True,
        description="Enables grounded conversational AI assistant interaction",
        beta_only=False,
        rollout_percentage=100,
    ),
    FeatureFlagKey.OPPORTUNITY_MONITORING: FeatureFlagState(
        key=FeatureFlagKey.OPPORTUNITY_MONITORING,
        enabled=True,
        description="Enables background change detection and monitoring sweeps",
        beta_only=False,
        rollout_percentage=100,
    ),
    FeatureFlagKey.PUSH_NOTIFICATIONS: FeatureFlagState(
        key=FeatureFlagKey.PUSH_NOTIFICATIONS,
        enabled=False,  # Controlled rollout: disabled by default in staging/beta
        description="Enables mobile device push notifications",
        beta_only=True,
        rollout_percentage=20,
    ),
    FeatureFlagKey.BETA_FEEDBACK_WIDGET: FeatureFlagState(
        key=FeatureFlagKey.BETA_FEEDBACK_WIDGET,
        enabled=True,
        description="Enables specialized in-app beta feedback and issue reporting",
        beta_only=True,
        rollout_percentage=100,
    ),
    FeatureFlagKey.EXPERIMENTAL_MULTILINGUAL: FeatureFlagState(
        key=FeatureFlagKey.EXPERIMENTAL_MULTILINGUAL,
        enabled=True,
        description="Enables multilingual concept bridges for Arabic, Urdu, Turkish",
        beta_only=False,
        rollout_percentage=100,
    ),
    FeatureFlagKey.APPLICATION_EXPORT: FeatureFlagState(
        key=FeatureFlagKey.APPLICATION_EXPORT,
        enabled=True,
        description="Enables exporting application deadlines and checklists",
        beta_only=False,
        rollout_percentage=100,
    ),
}


class FeatureFlagsService:
    """Manages runtime feature flags, allowing remote kill-switches and canary rollouts."""

    _instance: FeatureFlagsService | None = None

    def __init__(self) -> None:
        self._flags: dict[FeatureFlagKey, FeatureFlagState] = {
            k: v.model_copy() for k, v in DEFAULT_FEATURE_FLAGS.items()
        }

    @classmethod
    def get_instance(cls) -> FeatureFlagsService:
        if cls._instance is None:
            cls._instance = FeatureFlagsService()
        return cls._instance

    def is_enabled(
        self,
        flag_key: FeatureFlagKey | str,
        user_id: UUID | None = None,
    ) -> bool:
        """Evaluates whether a feature flag is active for the target user or system."""
        try:
            key = FeatureFlagKey(flag_key) if isinstance(flag_key, str) else flag_key
        except ValueError:
            logger.warning("Unrecognized feature flag checked: %s", flag_key)
            return False

        flag = self._flags.get(key)
        if flag is None or not flag.enabled:
            return False

        if flag.rollout_percentage >= 100 or user_id is None:
            return True

        # Deterministic cohort hashing for partial rollouts
        user_hash = hash(str(user_id)) % 100
        return user_hash < flag.rollout_percentage

    def set_flag(
        self,
        flag_key: FeatureFlagKey | str,
        enabled: bool,
        rollout_percentage: int | None = None,
    ) -> FeatureFlagState:
        """Dynamically updates a flag at runtime without server restart."""
        key = FeatureFlagKey(flag_key) if isinstance(flag_key, str) else flag_key
        if key not in self._flags:
            raise KeyError(f"Feature flag {key} does not exist")

        flag = self._flags[key]
        flag.enabled = enabled
        if rollout_percentage is not None:
            flag.rollout_percentage = max(0, min(100, rollout_percentage))

        logger.info(
            "Feature flag '%s' updated: enabled=%s, rollout=%d%%",
            key,
            flag.enabled,
            flag.rollout_percentage,
        )
        return flag

    def reset_defaults(self) -> None:
        """Resets all feature flags to initial safe defaults."""
        self._flags = {k: v.model_copy() for k, v in DEFAULT_FEATURE_FLAGS.items()}

    def get_client_flags(self) -> dict[str, bool]:
        """Returns key-value map for client app synchronization."""
        return {k.value: v.enabled for k, v in self._flags.items()}

    def get_all_states(self) -> list[FeatureFlagState]:
        """Returns full diagnostic state list for admin inspection."""
        return list(self._flags.values())


def get_feature_flags() -> FeatureFlagsService:
    return FeatureFlagsService.get_instance()
