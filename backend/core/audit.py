"""
Audit logging.

The Store collection holds raw records; this module is the single place
that knows the record shape, so future schema changes (new fields,
indexing strategies) happen here, not in every stage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo.collection import Collection


def log(audit: Collection, record: dict[str, Any]) -> None:
    if "created_at" not in record:
        record["created_at"] = datetime.now(timezone.utc)
    audit.insert_one(record)
