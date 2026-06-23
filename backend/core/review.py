"""
Shared review-state machinery.

Every stage that exposes items to HITL review (rules, analyses, gaps,
specs, TOC rows, shells, code) uses the same ReviewState shape so the
frontend can render them with one component and the backend can run the
same accept/edit/reject/approve operations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReviewStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class ReviewState(BaseModel):
    status: ReviewStatus = ReviewStatus.PENDING
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reason: Optional[str] = None
    edited_value: Optional[dict[str, Any]] = None
