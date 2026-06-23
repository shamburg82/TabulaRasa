"""
MongoDB storage layer (shared across stages).

The chunks collection serves two purposes today:
  1. Source-of-truth for parsed SAP/protocol/guidance sections, so the
     HITL review UI can surface the original passage that backed each
     extracted rule, analysis, or gap.
  2. A text-searchable corpus for ad-hoc lookups via /search.

A standard MongoDB $text index is used for search. Vector / semantic
retrieval was considered and intentionally deferred.

The Store is schema-agnostic: callers pass dicts that have already been
validated by their stage's Pydantic models. doc_type is a free-form
string (callers typically pass an enum's .value).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.collection import Collection
from pymongo.errors import OperationFailure

from .config import settings

logger = logging.getLogger(__name__)


class Store:
    def __init__(self, uri: str | None = None, db_name: str | None = None):
        self.client = MongoClient(uri or settings.mongo_uri)
        self.db = self.client[db_name or settings.mongo_db]
        self.documents: Collection = self.db[settings.coll_documents]
        self.chunks: Collection = self.db[settings.coll_chunks]
        self.extractions: Collection = self.db[settings.coll_extractions]
        self.toc_syntheses: Collection = self.db[settings.coll_toc_syntheses]
        self.audit: Collection = self.db[settings.coll_audit]

    # ------------------------------------------------------------------ #
    # Generic versioned-record helpers (used by stage pipelines)
    # ------------------------------------------------------------------ #

    def next_version(self, collection: Collection, study_id: str) -> int:
        latest = collection.find_one({"study_id": study_id}, sort=[("version", -1)])
        return (latest["version"] + 1) if latest else 1

    def save_versioned(self, collection: Collection, record: dict[str, Any]) -> None:
        collection.update_one(
            {"study_id": record["study_id"], "version": record["version"]},
            {"$set": record},
            upsert=True,
        )

    def get_versioned(self, collection: Collection, study_id: str,
                      version: Optional[int] = None) -> Optional[dict]:
        flt: dict[str, Any] = {"study_id": study_id}
        if version is not None:
            flt["version"] = version
        doc = collection.find_one(flt, sort=[("version", -1)])
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    # ------------------------------------------------------------------ #
    # Bootstrap
    # ------------------------------------------------------------------ #

    def ensure_indexes(self) -> None:
        self.documents.create_index([("study_id", ASCENDING), ("doc_type", ASCENDING)])
        self.documents.create_index([("sha256", ASCENDING)])
        self.chunks.create_index(
            [("document_id", ASCENDING), ("section_id", ASCENDING)], unique=True
        )
        self.chunks.create_index([("study_id", ASCENDING), ("doc_type", ASCENDING)])
        self.extractions.create_index(
            [("study_id", ASCENDING), ("version", ASCENDING)], unique=True
        )
        self.toc_syntheses.create_index(
            [("study_id", ASCENDING), ("version", ASCENDING)], unique=True
        )
        self.audit.create_index([("study_id", ASCENDING), ("created_at", ASCENDING)])
        try:
            self.chunks.create_index([("text", TEXT), ("title", TEXT)])
        except OperationFailure as exc:
            logger.warning("Could not create lexical text index: %s", exc)

    # ------------------------------------------------------------------ #
    # Document registry + chunk persistence
    # ------------------------------------------------------------------ #

    def register_document(
        self,
        *,
        study_id: Optional[str],
        doc_type: str,
        filename: str,
        file_bytes: bytes,
        version_tag: Optional[str] = None,
    ) -> str:
        sha = hashlib.sha256(file_bytes).hexdigest()
        existing = self.documents.find_one({"sha256": sha, "study_id": study_id})
        if existing:
            return str(existing["_id"])
        doc = {
            "study_id": study_id,
            "doc_type": doc_type,
            "filename": filename,
            "version_tag": version_tag,
            "sha256": sha,
            "status": "registered",
            "created_at": datetime.now(timezone.utc),
        }
        return str(self.documents.insert_one(doc).inserted_id)

    def save_chunks(
        self,
        *,
        document_id: str,
        study_id: Optional[str],
        doc_type: str,
        sections: list[dict],
    ) -> int:
        """Upsert section chunks. Sections are already-validated dicts."""
        count = 0
        for s in sections:
            payload = dict(s)
            payload.update(
                document_id=document_id,
                study_id=study_id,
                doc_type=doc_type,
                updated_at=datetime.now(timezone.utc),
            )
            self.chunks.update_one(
                {"document_id": document_id, "section_id": s["section_id"]},
                {"$set": payload},
                upsert=True,
            )
            count += 1
        self.documents.update_one(
            {"_id": self._oid(document_id)},
            {"$set": {"status": "chunked", "n_chunks": count}},
        )
        return count

    def get_sections(self, document_id: str) -> list[dict]:
        return list(self.chunks.find({"document_id": document_id}).sort("section_id", 1))

    # ------------------------------------------------------------------ #
    # Search ($text)
    # ------------------------------------------------------------------ #

    def search(
        self,
        query: str,
        *,
        study_id: Optional[str] = None,
        doc_types: Optional[list[str]] = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        flt: dict[str, Any] = {"$text": {"$search": query}}
        if study_id is not None:
            flt["study_id"] = study_id
        if doc_types:
            flt["doc_type"] = {"$in": list(doc_types)}
        cursor = (
            self.chunks.find(flt, {"score": {"$meta": "textScore"}, "_id": 0})
            .sort([("score", {"$meta": "textScore"})])
            .limit(limit)
        )
        return list(cursor)

    # ------------------------------------------------------------------ #
    # Extraction shortcuts (thin wrappers over the generic helpers)
    # ------------------------------------------------------------------ #

    def next_extraction_version(self, study_id: str) -> int:
        return self.next_version(self.extractions, study_id)

    def save_extraction(self, extraction: dict[str, Any]) -> None:
        self.save_versioned(self.extractions, extraction)

    def get_extraction(self, study_id: str, version: Optional[int] = None) -> Optional[dict]:
        return self.get_versioned(self.extractions, study_id, version)

    def log_audit(self, record: dict[str, Any]) -> None:
        self.audit.insert_one(record)

    @staticmethod
    def _oid(value: str):
        from bson import ObjectId
        return ObjectId(value)
