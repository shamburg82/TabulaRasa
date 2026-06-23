"""
Pydantic schemas for Stage 1 artifacts.

These shapes are the contract between the ingestion backend, the HITL
review UI, and Stage 2 (TOC/spec synthesis). Every extracted item carries
source citations (section number + page) and a review block so reviewer
decisions and rejection reasons can feed correction memory later.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------- #
# Source documents and chunks
# --------------------------------------------------------------------- #

class DocType(str, Enum):
    SAP = "sap"
    PROTOCOL = "protocol"
    GUIDANCE = "guidance"          # ICH E3/E9/E9R1, EMA 0070, HC PRCI, CT.gov
    HOUSE_STANDARD = "house_standard"
    SHELL_LIBRARY = "shell_library"


class DocumentSection(BaseModel):
    """One structurally-chunked section of a source document."""
    section_id: str                      # stable id, e.g. "s_0042"
    number: Optional[str] = None         # "9.4.1" if a numbered heading
    title: str
    level: int = 1                       # heading depth
    parent_id: Optional[str] = None
    text: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    char_count: int = 0


class SectionRole(str, Enum):
    """Semantic role assigned by the section-map pass."""
    ADMIN = "administrative"
    OBJECTIVES = "objectives_estimands"
    POPULATIONS = "analysis_populations"
    ENDPOINTS = "endpoints"
    STATISTICAL_METHODS = "statistical_methods"
    SAFETY = "safety_analyses"
    EFFICACY = "efficacy_analyses"
    AE_DEFINITIONS = "ae_definitions"
    MISSING_DATA = "missing_data_handling"
    INTERIM = "interim_analyses"
    MULTIPLICITY = "multiplicity"
    SUBGROUPS = "subgroups"
    VISITS = "visit_windows"
    DERIVATIONS = "derived_variables"
    CHANGES = "changes_from_protocol"
    REFERENCES = "references"
    OTHER = "other"


# --------------------------------------------------------------------- #
# Review / HITL
# --------------------------------------------------------------------- #

# Re-exported from core.review so every stage shares one definition.
from core.review import ReviewState, ReviewStatus  # noqa: F401


class Citation(BaseModel):
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    section_id: Optional[str] = None
    page: Optional[int] = None
    quote: Optional[str] = None          # short verbatim anchor for the reviewer UI


# --------------------------------------------------------------------- #
# Extracted items
# --------------------------------------------------------------------- #

class RuleScope(str, Enum):
    GLOBAL = "global"
    SAFETY_ONLY = "safety_only"
    EFFICACY_ONLY = "efficacy_only"
    DOMAIN = "domain_specific"
    POPULATION = "population_specific"


class RuleOrigin(str, Enum):
    EXTRACTED = "extracted"
    USER_ADDED = "user_added"


class ExtractedRule(BaseModel):
    """A cross-cutting rule that drives many analyses downstream."""
    rule_id: str                         # "R-001"
    confidence: Optional[float] = None
    origin: RuleOrigin = RuleOrigin.EXTRACTED 
    statement: str                       # normalized rule text
    scope: RuleScope
    scope_detail: Optional[str] = None   # e.g. "AE tables only", "FAS"
    category: str                        # treatment_assignment, population, imputation, ...
    citations: list[Citation] = Field(default_factory=list)
    rationale: Optional[str] = None
    review: ReviewState = Field(default_factory=ReviewState)


class AnalysisOrigin(str, Enum):
    EXPLICIT = "explicit"                # directly described in the SAP
    IMPLIED = "implied"                  # required by convention / ICH E3 / house standard


class ExtractedAnalysis(BaseModel):
    analysis_id: str                     # "A-001"
    confidence: Optional[float] = None
    origin: AnalysisOrigin
    title: str
    output_type: Optional[str] = None    # T / L / F if inferable
    endpoint: Optional[str] = None
    population: Optional[str] = None
    method: Optional[str] = None         # statistical method summary
    comparison: Optional[str] = None
    visit_structure: Optional[str] = None
    subgroups: list[str] = Field(default_factory=list)
    applicable_rules: list[str] = Field(default_factory=list)   # rule_ids
    convention_basis: Optional[str] = None  # for implied: which convention requires it
    citations: list[Citation] = Field(default_factory=list)
    rationale: Optional[str] = None
    review: ReviewState = Field(default_factory=ReviewState)


class IdentifiedGap(BaseModel):
    gap_id: str                          # "G-001"
    confidence: Optional[float] = None
    description: str                     # what is missing relative to ICH / house defaults
    affected_area: str                   # e.g. "missing data handling for PRO endpoints"
    proposed_default: Optional[str] = None
    default_source: Optional[str] = None # which house standard / guidance the default comes from
    rationale: Optional[str] = None
    citations: list[Citation] = Field(default_factory=list)
    review: ReviewState = Field(default_factory=ReviewState)


class SectionMapEntry(BaseModel):
    section_id: str
    number: Optional[str] = None
    title: str
    roles: list[SectionRole] = Field(default_factory=list)


# --------------------------------------------------------------------- #
# Top-level Stage 1 output:  sap_extraction_v{n}
# --------------------------------------------------------------------- #

class ExtractionStatus(str, Enum):
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    FAILED = "failed"


class SapExtraction(BaseModel):
    study_id: str
    sap_document_id: str                 # _id of the source doc in `documents`
    version: int = 1
    status: ExtractionStatus = ExtractionStatus.RUNNING
    section_map: list[SectionMapEntry] = Field(default_factory=list)
    rules: list[ExtractedRule] = Field(default_factory=list)
    analyses: list[ExtractedAnalysis] = Field(default_factory=list)
    gaps: list[IdentifiedGap] = Field(default_factory=list)
    pass_progress: dict[str, str] = Field(default_factory=dict)  # pass name -> done/failed
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------- #

class AuditRecord(BaseModel):
    study_id: str
    stage: str = "stage1_ingestion"
    action: str                          # e.g. "pass:rule_extraction"
    model_id: str
    temperature: float
    prompt_sha256: str
    response_sha256: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow)
