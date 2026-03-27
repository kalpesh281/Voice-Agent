from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    """Abstract base repository — implement for MongoDB now, SQL later."""

    @abstractmethod
    async def find_one(self, filter: dict[str, Any]) -> dict | None:
        ...

    @abstractmethod
    async def find_many(
        self,
        filter: dict[str, Any],
        sort: list[tuple[str, int]] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        ...

    @abstractmethod
    async def insert_one(self, document: dict[str, Any]) -> str:
        ...

    @abstractmethod
    async def update_one(
        self, filter: dict[str, Any], update: dict[str, Any]
    ) -> bool:
        ...

    @abstractmethod
    async def count(self, filter: dict[str, Any]) -> int:
        ...

    @abstractmethod
    async def distinct(self, field: str, filter: dict[str, Any] | None = None) -> list:
        ...
