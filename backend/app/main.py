"""
Single FastAPI entrypoint, mounts every stage's routes.

Run with:  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.llm import configure_bedrock_llm
from core.store import Store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    llm = configure_bedrock_llm()
    if llm is None:
        raise RuntimeError(
            "Bedrock LLM configuration failed; check MODEL_EXTRACTION / "
            "MODEL_FALLBACK and the backend's AWS role permissions."
        )
    store = Store()
    store.ensure_indexes()

    # --- Stage 1 ---
    from sap_ingestion.extraction import ExtractionAgent
    from sap_ingestion.pipeline import IngestionPipeline
    import sap_ingestion.api as stage1_api

    stage1_pipeline = IngestionPipeline(
        store=store,
        agent=ExtractionAgent(llm=llm, audit_sink=store.log_audit),
    )
    stage1_api.pipeline = stage1_pipeline
    app.include_router(stage1_api.router)

    # --- Stage 2 ---
    from toc_synthesis.api import router as toc_router, set_pipeline as set_toc_pipeline
    from toc_synthesis.library import build_library
    from toc_synthesis.pipeline import TocPipeline
    from toc_synthesis.synthesis import SynthesisAgent

    toc_library = build_library()
    toc_pipeline = TocPipeline(
        store=store, library=toc_library,
        agent=SynthesisAgent(library=toc_library, llm=llm, audit_sink=store.log_audit),
    )
    set_toc_pipeline(toc_pipeline)
    app.include_router(toc_router)

    yield
    store.client.close()


app = FastAPI(title="TLF Automation", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
