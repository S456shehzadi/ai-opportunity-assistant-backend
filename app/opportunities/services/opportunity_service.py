from abc import ABC, abstractmethod

from app.opportunities.schemas.opportunity import (
    OpportunityCategory,
    OpportunityCreate,
    OpportunityRead,
)


class OpportunityService(ABC):
    """Abstract service layer for querying and managing validated opportunities."""

    @abstractmethod
    async def get_by_id(self, opportunity_id: str) -> OpportunityRead | None:
        pass

    @abstractmethod
    async def list_active(
        self,
        category: OpportunityCategory | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[OpportunityRead]:
        pass

    @abstractmethod
    async def create_opportunity(self, data: OpportunityCreate) -> OpportunityRead:
        pass
