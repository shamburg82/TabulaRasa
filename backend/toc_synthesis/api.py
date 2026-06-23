"""
Stage 2 HTTP surface.

Endpoints follow the same shape as Stage 1 so the React frontend can reuse
its review components:

  POST /studies/{study_id}/toc                       trigger synthesis
  GET  /studies/{study_id}/toc                       latest TOC + specs
  POST /studies/{study_id}/toc/{v}/review            accept/edit/reject one item
  POST /studies/{study_id}/toc/{v}/approve           lock the synthesis
  GET  /archetypes                                   inspect the loaded library
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from .pipeline import TocPipeline
from .schemas import NumberingScheme

router = APIRouter(prefix="", tags=["toc"])

# The pipeline is set once at startup by main.py
_pipeline: Optional[TocPipeline] = None


def set_pipeline(pipeline: TocPipeline) -> None:
    global _pipeline
    _pipeline = pipeline


def _pl() -> TocPipeline:
    if _pipeline is None:
        raise HTTPException(503, "TOC pipeline not initialised")
    return _pipeline


class SynthesizeRequest(BaseModel):
    extraction_version: Optional[int] = None
    scheme: Optional[NumberingScheme] = None
    library_version: Optional[str] = None


class ReviewRequest(BaseModel):
    item_kind: str
    item_id: str
    status: str
    reviewer: str
    reason: Optional[str] = None
    edited_value: Optional[dict] = None


class ApproveRequest(BaseModel):
    reviewer: str


@router.post("/studies/{study_id}/toc", status_code=202)
def synthesize(study_id: str, body: SynthesizeRequest = Body(default=SynthesizeRequest())):
    try:
        return _pl().synthesize(
            study_id=study_id,
            extraction_version=body.extraction_version,
            scheme=body.scheme,
            library_version=body.library_version,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/studies/{study_id}/toc")
def get_toc(study_id: str, version: Optional[int] = None):
    doc = _pl().get(study_id, version)
    if not doc:
        raise HTTPException(404, f"No Stage 2 synthesis for study {study_id}")
    return doc


@router.post("/studies/{study_id}/toc/{version}/review")
def review_item(study_id: str, version: int, body: ReviewRequest):
    try:
        return _pl().apply_review(
            study_id=study_id, version=version,
            item_kind=body.item_kind, item_id=body.item_id,
            status=body.status, reviewer=body.reviewer,
            reason=body.reason, edited_value=body.edited_value,
        )
    except (ValueError, LookupError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/studies/{study_id}/toc/{version}/approve")
def approve(study_id: str, version: int, body: ApproveRequest):
    try:
        return _pl().approve(
            study_id=study_id, version=version, reviewer=body.reviewer
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/archetypes")
def list_archetypes():
    return {"archetypes": [a.model_dump() for a in _pl().library.list_archetypes()],
            "conventions": _pl().library.list_conventions()}
