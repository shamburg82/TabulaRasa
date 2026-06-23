"""
FastAPI surface for Stage 1.

Deployable to Posit Connect as a FastAPI app (entrypoint sap_ingestion.api:app).
Set MONGO_URI, AWS_REGION, MODEL_EXTRACTION, etc. as environment variables in
the Connect content settings; Bedrock access flows through the instance role
or the configured AWS credentials.

Endpoints:
  POST /studies/{study_id}/sap                  upload SAP, kick off extraction (background)
  GET  /studies/{study_id}/extraction           latest (or ?version=) extraction record
  POST /studies/{study_id}/extraction/{v}/review   accept/edit/reject one item
  POST /studies/{study_id}/extraction/{v}/approve  lock the extraction (gates Stage 2)
  GET  /studies/{study_id}/audit                Audit records for a study, optionally filtered by stage
  GET  /studies                                 Drives the landing page
  POST /reference                               ingest guidance / house standards / protocol
  POST /search                                  RAG query over the chunk store
  GET  /healthz
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
import getpass

from fastapi import APIRouter, BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import settings
from .pipeline import IngestionPipeline
from .schemas import DocType, RuleScope

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)

pipeline: Optional[IngestionPipeline] = None


# ---------------------------------------------------------------------- #
# Request models
# ---------------------------------------------------------------------- #

class ReviewRequest(BaseModel):
    item_kind: str               # rules | analyses | gaps
    item_id: str
    status: str                  # accepted | edited | rejected
    reviewer: str
    reason: Optional[str] = None
    edited_value: Optional[dict] = None


class ApproveRequest(BaseModel):
    reviewer: str


class SearchRequest(BaseModel):
    query: str
    study_id: Optional[str] = None
    doc_types: Optional[list[DocType]] = None
    limit: int = 8


class AddRuleRequest(BaseModel):
    statement: str
    scope: str                           # RuleScope value: global | safety_only | efficacy_only | domain_specific | population_specific
    scope_detail: Optional[str] = None
    category: str
    rationale: Optional[str] = None
    reviewer: str



# ---------------------------------------------------------------------- #
# Router (mounted by app.main; also attached to the self-contained app)
# ---------------------------------------------------------------------- #

router = APIRouter(tags=["stage1"])

@router.get("/me")
def get_me(request: Request):
    """Best-effort current-user resolution.

    Posit Connect injects user identity via headers; behind a reverse proxy
    we look for X-Forwarded-User; in Posit Workbench the process runs as
    the logged-in OS user."""
    h = request.headers
    for key in ("posit-connect-user-name", "rstudio-connect-credentials",
                "x-forwarded-user", "x-auth-user", "x-remote-user"):
        value = h.get(key)
        if value:
            return {"username": value, "source": key}
    try:
        import getpass
        return {"username": getpass.getuser(), "source": "os"}
    except Exception:
        return {"username": "anonymous", "source": "fallback"}


@router.post("/studies/{study_id}/sap", status_code=202)
async def upload_sap(
    study_id: str,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    version_tag: Optional[str] = Form(None),
    house_standards: str = Form(""),
):
    """Register the SAP and run the 5-pass extraction in the background.
    Poll GET /studies/{study_id}/extraction for pass_progress and status."""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "Empty file")
    background.add_task(
        pipeline.ingest_sap,
        file_bytes=file_bytes,
        filename=file.filename or "sap.pdf",
        study_id=study_id,
        version_tag=version_tag,
        house_standards=house_standards,
    )
    return {"study_id": study_id, "status": "accepted",
            "detail": "Extraction started; poll the extraction endpoint for progress."}


@router.get("/studies/{study_id}/extraction")
def get_extraction(study_id: str, version: Optional[int] = None):
    doc = pipeline.store.get_extraction(study_id, version)
    if not doc:
        raise HTTPException(404, f"No extraction found for study {study_id}")
    return doc


@router.post("/studies/{study_id}/extraction/{version}/review")
def review_item(study_id: str, version: int, body: ReviewRequest):
    try:
        return pipeline.apply_review(
            study_id=study_id, version=version,
            item_kind=body.item_kind, item_id=body.item_id,
            status=body.status, reviewer=body.reviewer,
            reason=body.reason, edited_value=body.edited_value,
        )
    except (ValueError, LookupError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/studies/{study_id}/extraction/{version}/approve")
def approve(study_id: str, version: int, body: ApproveRequest):
    try:
        return pipeline.approve_extraction(
            study_id=study_id, version=version, reviewer=body.reviewer
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/studies/{study_id}/extraction/{version}/rules")
def add_user_rule(study_id: str, version: int, body: AddRuleRequest):
    """Append a user-defined rule to an existing extraction.
    Pre-marked as accepted because the user authored it.
    """
    try:
        return pipeline.add_user_rule(
            study_id=study_id, version=version,
            statement=body.statement, scope=body.scope,
            scope_detail=body.scope_detail, category=body.category,
            rationale=body.rationale, reviewer=body.reviewer,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/studies/{study_id}/audit")
def get_audit(study_id: str, stage: Optional[str] = None):
    """Audit records for a study, optionally filtered by stage."""
    return pipeline.store.get_audit(study_id, stage=stage)


@router.get("/studies")
def list_studies():
    """One row per study with its latest extraction. Drives the landing page."""
    return pipeline.store.list_studies()


@router.post("/reference")
async def upload_reference(
    file: UploadFile = File(...),
    doc_type: DocType = Form(...),
    study_id: Optional[str] = Form(None),
    version_tag: Optional[str] = Form(None),
):
    """Ingest guidance (ICH E3/E9, EMA 0070, ...), house standards, or a
    protocol into the corpus. study_id=None means shared across studies."""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "Empty file")
    if doc_type == DocType.SAP:
        raise HTTPException(400, "Use the /studies/{study_id}/sap endpoint for SAPs")
    return pipeline.ingest_reference(
        file_bytes=file_bytes, filename=file.filename or "reference.pdf",
        doc_type=doc_type, study_id=study_id, version_tag=version_tag,
    )


@router.post("/search")
def search(body: SearchRequest):
    """Text search over the chunk store (MongoDB $text index)."""
    return {
        "results": pipeline.store.search(
            body.query, study_id=body.study_id,
            doc_types=body.doc_types, limit=body.limit,
        )
    }


@router.get("/healthz")
def healthz():
    pipeline.store.client.admin.command("ping")
    return {"status": "ok"}


# ---------------------------------------------------------------------- #
# Self-contained app (legacy entrypoint: uvicorn sap_ingestion.api:app)
# Mounts only Stage 1. For the unified app with all stages,
# use app.main:app instead.
# ---------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    from .extraction import ExtractionAgent
    from core.llm import configure_bedrock_llm
    from core.store import Store

    llm = configure_bedrock_llm()
    if llm is None:
        raise RuntimeError(
            "Bedrock LLM configuration failed; check MODEL_EXTRACTION / "
            "MODEL_FALLBACK and the backend's AWS role permissions."
        )
    store = Store()
    store.ensure_indexes()
    pipeline = IngestionPipeline(
        store=store,
        agent=ExtractionAgent(llm=llm, audit_sink=store.log_audit),
    )

    yield
    store.client.close()


app = FastAPI(title="TLF Automation: SAP Ingestion (Stage 1)", lifespan=lifespan)


# Resolve allowed origins from settings if present, else straight from env,
# so the app stands up even against an older/custom config.py.
# _cors_origins = getattr(settings, "cors_allow_origins", None) or [
#     o.strip()
#     for o in os.environ.get(
#         "CORS_ALLOW_ORIGINS", "http://localhost:5173,http://localhost:3000"
#     ).split(",")
#     if o.strip()
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)