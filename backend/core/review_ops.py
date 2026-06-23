"""
Generic review operations against any "items" collection.

A stage stores its versioned artifact with one or more item lists (e.g.
rules / analyses / gaps for Stage 1; specs / toc for Stage 2). Each item
carries a unique id field and a `review` block conforming to ReviewState.

apply_review() and approve() work across stages by parameterizing:
  collection         the Mongo collection holding versioned records
  item_kind          which array on the record holds the items
  id_field           which key inside an item is its primary id
  pending_kinds      which arrays are considered for the approval gate
                     (typically the same as item_kind for that stage)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pymongo.collection import Collection


def apply_review(
    *,
    collection: Collection,
    study_id: str,
    version: int,
    item_kind: str,
    id_field: str,
    item_id: str,
    status: str,
    reviewer: str,
    reason: Optional[str] = None,
    edited_value: Optional[dict] = None,
) -> dict:
    if status == "rejected" and not reason:
        raise ValueError("A reason is required when rejecting an item")
    review = {
        "status": status,
        "reviewer": reviewer,
        "reviewed_at": datetime.now(timezone.utc),
        "reason": reason,
        "edited_value": edited_value,
    }
    result = collection.update_one(
        {"study_id": study_id, "version": version, f"{item_kind}.{id_field}": item_id},
        {"$set": {f"{item_kind}.$.review": review,
                  "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise LookupError(f"{item_kind[:-1]} {item_id} not found in v{version}")
    return {"item_id": item_id, "status": status}


def approve_record(
    *,
    collection: Collection,
    study_id: str,
    version: int,
    reviewer: str,
    pending_kinds: list[str],
    approved_status: str = "approved",
) -> dict:
    """Lock a record once all items in pending_kinds are out of 'pending'."""
    doc = collection.find_one({"study_id": study_id, "version": version})
    if not doc:
        raise LookupError(f"No v{version} for study {study_id}")
    pending: list[str] = []
    for kind in pending_kinds:
        for item in doc.get(kind, []):
            if item.get("review", {}).get("status", "pending") == "pending":
                # pick whichever *_id key is present
                for key in ("rule_id", "analysis_id", "gap_id", "spec_id", "row_id"):
                    if key in item:
                        pending.append(item[key])
                        break
    if pending:
        raise ValueError(f"{len(pending)} items still pending review: {pending[:10]}")
    collection.update_one(
        {"study_id": study_id, "version": version},
        {"$set": {"status": approved_status,
                  "approved_by": reviewer,
                  "approved_at": datetime.now(timezone.utc)}},
    )
    return {"study_id": study_id, "version": version, "status": approved_status}
