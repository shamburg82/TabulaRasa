"""
End-to-end Stage 1 pipeline.

ingest_sap()       parse -> chunk -> persist (auto-embedded) -> 5-pass
                   extraction -> versioned sap_extraction record awaiting
                   HITL review.
ingest_reference() parse + persist guidance / house standards / protocol
                   into the shared corpus (no extraction passes); these
                   become retrievable context for later stages.

Designed to run as a long-running background job (FastAPI BackgroundTasks
here; swap for a queue worker without changing this module's interface).
"""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .extraction import ExtractionAgent
from .parser import parse_document
from .schemas import DocType, ExtractionStatus, SapExtraction
from core.review_ops import apply_review, approve_record
from core.store import Store

logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(self, store: Optional[Store] = None, agent: Optional[ExtractionAgent] = None):
        self.store = store or Store()
        self.agent = agent or ExtractionAgent(audit_sink=self.store.log_audit)

    # ------------------------------------------------------------------ #

    def ingest_reference(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        doc_type: DocType,
        study_id: Optional[str] = None,
        version_tag: Optional[str] = None,
    ) -> dict:
        """Guidance corpus / house standards / protocol: parse and store only."""
        document_id = self.store.register_document(
            study_id=study_id, doc_type=doc_type.value, filename=filename,
            file_bytes=file_bytes, version_tag=version_tag,
        )
        sections = _parse_bytes(file_bytes, filename)
        n = self.store.save_chunks(
            document_id=document_id, study_id=study_id, doc_type=doc_type.value,
            sections=[s.model_dump() for s in sections],
        )
        return {"document_id": document_id, "n_chunks": n, "doc_type": doc_type.value}

    # ------------------------------------------------------------------ #

    def ingest_sap(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        study_id: str,
        version_tag: Optional[str] = None,
        house_standards: str = "",
    ) -> dict:
        """Full Stage 1: returns the saved extraction record (sync variant)."""
        document_id = self.store.register_document(
            study_id=study_id, doc_type=DocType.SAP.value, filename=filename,
            file_bytes=file_bytes, version_tag=version_tag,
        )
        sections = _parse_bytes(file_bytes, filename)
        self.store.save_chunks(
            document_id=document_id, study_id=study_id,
            doc_type=DocType.SAP.value,
            sections=[s.model_dump() for s in sections],
        )

        version = self.store.next_extraction_version(study_id)
        extraction = SapExtraction(
            study_id=study_id, sap_document_id=document_id, version=version,
            status=ExtractionStatus.RUNNING,
        )
        self.store.save_extraction(extraction.model_dump())

        def progress(pass_name: str, state: str) -> None:
            extraction.pass_progress[pass_name] = state
            extraction.updated_at = datetime.now(timezone.utc)
            self.store.save_extraction(extraction.model_dump())

        try:
            results = self.agent.run(
                sections, study_id=study_id,
                house_standards=house_standards, progress=progress,
            )
            extraction.section_map = results["section_map"]
            extraction.rules = results["rules"]
            extraction.analyses = results["analyses"]
            extraction.gaps = results["gaps"]
            extraction.status = ExtractionStatus.AWAITING_REVIEW
        except Exception as exc:  # noqa: BLE001 - job boundary, persist failure state
            logger.exception("SAP extraction failed for study %s", study_id)
            extraction.status = ExtractionStatus.FAILED
            extraction.error = str(exc)
        extraction.updated_at = datetime.now(timezone.utc)
        self.store.save_extraction(extraction.model_dump())
        return self.store.get_extraction(study_id, version)

    # ------------------------------------------------------------------ #
    # HITL review operations
    # ------------------------------------------------------------------ #

    def apply_review(
        self,
        *,
        study_id: str,
        version: int,
        item_kind: str,            # "rules" | "analyses" | "gaps"
        item_id: str,
        status: str,               # accepted | edited | rejected
        reviewer: str,
        reason: Optional[str] = None,
        edited_value: Optional[dict] = None,
    ) -> dict:
        if item_kind not in ("rules", "analyses", "gaps"):
            raise ValueError(f"Unknown item kind: {item_kind}")
        id_field = {"rules": "rule_id", "analyses": "analysis_id", "gaps": "gap_id"}[item_kind]
        return apply_review(
            collection=self.store.extractions,
            study_id=study_id, version=version,
            item_kind=item_kind, id_field=id_field, item_id=item_id,
            status=status, reviewer=reviewer, reason=reason, edited_value=edited_value,
        )

    def approve_extraction(self, *, study_id: str, version: int, reviewer: str) -> dict:
        """Lock the extraction; pending items block approval."""
        return approve_record(
            collection=self.store.extractions,
            study_id=study_id, version=version, reviewer=reviewer,
            pending_kinds=["rules", "analyses", "gaps"],
            approved_status=ExtractionStatus.APPROVED.value,
        )


def _parse_bytes(file_bytes: bytes, filename: str):
    suffix = Path(filename).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        return parse_document(tmp.name)
