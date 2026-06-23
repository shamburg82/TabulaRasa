"""
Stage 2 pipeline: orchestrate synthesis, persist versioned results.

Storage extends the Mongo layer used by Stage 1 (one new collection,
toc_syntheses, indexed on study_id + version). HITL review and approval
mirror the Stage 1 flow, with the same pending->accepted/edited/rejected
state machine on each spec/TOC row.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from core.review_ops import apply_review, approve_record
from core.store import Store

from .library import ArchetypeLibrary, build_library
from .schemas import NumberingScheme, SynthesisStatus, TocSynthesis
from .synthesis import SynthesisAgent

logger = logging.getLogger(__name__)


class TocPipeline:
    def __init__(
        self,
        *,
        store: Optional[Store] = None,
        library: Optional[ArchetypeLibrary] = None,
        agent: Optional[SynthesisAgent] = None,
    ):
        self.store = store or Store()
        # If no library supplied, the factory picks based on config.
        self._default_library = library or build_library()
        self._default_agent = agent or SynthesisAgent(
            library=self._default_library, audit_sink=self.store.log_audit,
        )
        self.coll = self.store.toc_syntheses

    def ensure_indexes(self) -> None:
        # Index is also ensured by Store.ensure_indexes; safe to repeat.
        pass

    # ------------------------------------------------------------------ #
    # Synthesis
    # ------------------------------------------------------------------ #

    def synthesize(
        self,
        *,
        study_id: str,
        extraction_version: Optional[int] = None,
        scheme: Optional[NumberingScheme] = None,
        library_version: Optional[str] = None,
    ) -> dict:
        """Run Stage 2 against the given (or latest approved) Stage 1 extraction.

        library_version selects which shell-library version to use for this
        run. Leave None to use SHELL_LIBRARY_DEFAULT_VERSION (i.e. the
        default agent configured at init).
        """
        extraction = self.store.get_extraction(study_id, extraction_version)
        if not extraction:
            raise LookupError(f"No Stage 1 extraction for study {study_id}")
        if extraction.get("status") != "approved":
            raise ValueError(
                f"Stage 1 extraction v{extraction['version']} is "
                f"'{extraction.get('status')}'; must be 'approved' before Stage 2."
            )

        if library_version:
            library = build_library(version_tag=library_version)
            agent = SynthesisAgent(
                library=library, llm=self._default_agent.llm,
                audit_sink=self.store.log_audit,
            )
            effective_version = library_version
        else:
            library = self._default_library
            agent = self._default_agent
            from core.config import settings as _s
            effective_version = _s.shell_library_default_version

        version = self.store.next_version(self.coll, study_id)
        scheme = scheme or NumberingScheme()
        synthesis = TocSynthesis(
            study_id=study_id,
            sap_extraction_version=extraction["version"],
            version=version,
            status=SynthesisStatus.RUNNING,
            numbering_scheme=scheme,
        )
        record = synthesis.model_dump()
        record["library_version"] = effective_version
        self.store.save_versioned(self.coll, record)

        def progress(pass_name: str, state: str) -> None:
            synthesis.progress[pass_name] = state
            synthesis.updated_at = datetime.now(timezone.utc)
            record = synthesis.model_dump()
            record["library_version"] = effective_version
            self.store.save_versioned(self.coll, record)

        try:
            results = agent.run(
                study_id=study_id, extraction=extraction,
                scheme=scheme, progress=progress,
            )
            synthesis.toc = results["toc"]
            synthesis.specs = results["specs"]
            synthesis.status = SynthesisStatus.AWAITING_REVIEW
        except Exception as exc:  # noqa: BLE001
            logger.exception("Stage 2 synthesis failed for study %s", study_id)
            synthesis.status = SynthesisStatus.FAILED
            synthesis.error = str(exc)
        synthesis.updated_at = datetime.now(timezone.utc)
        record = synthesis.model_dump()
        record["library_version"] = effective_version
        self.store.save_versioned(self.coll, record)
        return self.get(study_id, version)

    # ------------------------------------------------------------------ #
    # HITL operations (delegated to core)
    # ------------------------------------------------------------------ #

    def apply_review(
        self,
        *,
        study_id: str,
        version: int,
        item_kind: str,            # "specs" | "toc"
        item_id: str,
        status: str,
        reviewer: str,
        reason: Optional[str] = None,
        edited_value: Optional[dict] = None,
    ) -> dict:
        if item_kind not in ("specs", "toc"):
            raise ValueError(f"Unknown item kind: {item_kind}")
        id_field = {"specs": "spec_id", "toc": "row_id"}[item_kind]
        return apply_review(
            collection=self.coll,
            study_id=study_id, version=version,
            item_kind=item_kind, id_field=id_field, item_id=item_id,
            status=status, reviewer=reviewer, reason=reason, edited_value=edited_value,
        )

    def approve(self, *, study_id: str, version: int, reviewer: str) -> dict:
        return approve_record(
            collection=self.coll,
            study_id=study_id, version=version, reviewer=reviewer,
            pending_kinds=["specs"],
            approved_status=SynthesisStatus.APPROVED.value,
        )

    # ------------------------------------------------------------------ #
    # Storage helpers
    # ------------------------------------------------------------------ #

    def get(self, study_id: str, version: Optional[int] = None) -> Optional[dict]:
        return self.store.get_versioned(self.coll, study_id, version)

    @property
    def library(self) -> ArchetypeLibrary:
        return self._default_library
