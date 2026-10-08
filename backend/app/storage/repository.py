"""MongoDB repository for MRI study and processing-job metadata."""

from functools import lru_cache
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection

from app.config import Settings, get_settings


class MongoRepository:
    """Store queryable metadata in MongoDB; keep large imaging files on disk."""

    def __init__(self, settings: Settings):
        self.client = MongoClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        )
        self.db = self.client[settings.mongodb_database]

    def ping(self) -> None:
        self.client.admin.command("ping")

    def close(self) -> None:
        self.client.close()

    def collection(self, name: str) -> Collection:
        return self.db[name]

    def save(self, collection: str, key: str, value: dict[str, Any]) -> None:
        self.collection(collection).replace_one({"_id": key}, {"_id": key, **value}, upsert=True)

    def get(self, collection: str, key: str) -> dict[str, Any] | None:
        document = self.collection(collection).find_one({"_id": key})
        if document is None:
            return None
        document.pop("_id", None)
        return document

    def list(self, collection: str, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Return metadata in newest-first order with bounded pagination."""
        cursor = self.collection(collection).find().sort("created_at", -1).skip(offset).limit(limit)
        documents: list[dict[str, Any]] = []
        for document in cursor:
            document.pop("_id", None)
            documents.append(document)
        return documents

    def count(self, collection: str) -> int:
        return self.collection(collection).count_documents({})

    def delete(self, collection: str, key: str) -> bool:
        return self.collection(collection).delete_one({"_id": key}).deleted_count == 1


@lru_cache
def get_repository() -> MongoRepository:
    return MongoRepository(get_settings())


def close_repository() -> None:
    if get_repository.cache_info().currsize:
        get_repository().close()
    get_repository.cache_clear()
