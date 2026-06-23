"""
Pydantic schemas for Stage 2 artifacts.

These are the contract between Stage 2 synthesis, the HITL TOC review UI,
and Stage 3 shell generation. Each TOC row corresponds to a single
deliverable output; multiple rows can link back to the same Stage 1
analysis_id (the AE summary spawning a table, a listing, and possibly a
figure all carry the same analysis_id).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

# Shared HITL review machinery
from core.review import ReviewState, ReviewStatus  # noqa: F401


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------- #
# Numbering scheme (configurable; default per user spec)
# --------------------------------------------------------------------- #

class OutputType(str, Enum):
    TABLE = "T"
    LISTING = "L"
    FIGURE = "F"


class OutputCategory(str, Enum):
    """Topical bucket that drives the second tuple of the output number."""
    BASELINE = "baseline"        # 9.1.x / 10.1.x
    EFFICACY = "efficacy"        # 9.2.x / 10.2.x
    SAFETY = "safety"            # 9.3.x / 10.3.x
    DISCLOSURE = "disclosure"    # 9.4.x / 10.4.x


class NumberingScheme(BaseModel):
    """
    Configurable hierarchical output numbering.

    Defaults match the user-specified house convention:
      tables/figures use root 9, listings use root 10.
      Top-level category map: baseline=1, efficacy=2, safety=3, disclosure=4.

    Sub-categories (optional, per top category):
      sub_category_map is a dict keyed by top-category name, whose value is
      another dict mapping sub-category name -> integer position. When a
      spec carries an output_sub_category that exists in the map for its
      top category, the number includes an extra level
      (e.g. 9.3.2.x for safety/ae). When not provided, behavior is
      unchanged (9.3.x).

    Example house convention:
        sub_category_map = {
            "safety": {"exposure": 1, "ae": 2, "labs": 3, "vitals": 4, "ecg": 5},
            "efficacy": {"primary": 1, "secondary": 2, "exploratory": 3},
        }

    Output IDs prefix the type: t-, l-, f-.
    """
    table_root: int = 9
    listing_root: int = 10
    figure_shares_table_root: bool = True
    category_map: dict[str, int] = Field(
        default_factory=lambda: {"baseline": 1, "efficacy": 2, "safety": 3, "disclosure": 4}
    )
    # Optional fourth tuple. Keys are top-category names; values are
    # name->position maps for that top category. A top category absent
    # from this dict (or assigned an empty map) keeps three-level numbers.
    sub_category_map: dict[str, dict[str, int]] = Field(default_factory=dict)

    def build_number(
        self,
        output_type: "OutputType",
        category: "OutputCategory",
        seq: int,
        sub_category: Optional[str] = None,
    ) -> str:
        cat_n = self.category_map[category.value]
        if output_type == OutputType.LISTING:
            root = self.listing_root
        elif output_type == OutputType.FIGURE and not self.figure_shares_table_root:
            root = self.table_root
        else:
            root = self.table_root
        subs = self.sub_category_map.get(category.value, {}) or {}
        if sub_category and sub_category in subs:
            return f"{root}.{cat_n}.{subs[sub_category]}.{seq}"
        return f"{root}.{cat_n}.{seq}"

    def build_output_id(self, output_type: "OutputType", number: str) -> str:
        return f"{output_type.value.lower()}-{number}"

    def has_sub_categories(self, category: "OutputCategory") -> bool:
        return bool(self.sub_category_map.get(category.value))

    def sub_categories_for(self, category: "OutputCategory") -> list[str]:
        return list((self.sub_category_map.get(category.value) or {}).keys())


# --------------------------------------------------------------------- #
# Analysis spec building blocks
# --------------------------------------------------------------------- #

class StatisticSet(BaseModel):
    """
    A set of statistics applied to a row-group. Per the user spec,
    statistic sets live at the row-group level (a block of rows shares
    one set, e.g. continuous stats {n, mean, SD, median, min, max} for
    an "Age" row group, or categorical stats {n, %} for "Sex").
    """
    set_id: str                              # "stats_continuous_default"
    name: str
    statistics: list[str]                    # ["n", "mean", "sd", "median", "min", "max"]
    decimal_precision: dict[str, int] = Field(default_factory=dict)
    # Optional: where it came from when synthesized from the library
    source_archetype: Optional[str] = None


class RowGroup(BaseModel):
    """A block of rows in the analysis output."""
    group_id: str
    label: str
    statistic_set_id: str
    source_variable: Optional[str] = None    # ADaM variable (resolved Stage 4)
    sort_order: int = 0


class TreatmentColumn(BaseModel):
    column_id: str
    label: str
    treatment_code: Optional[str] = None     # e.g. "PLB", "X-50", "X-75"
    is_total: bool = False
    show_n: bool = True


class AnalysisSpec(BaseModel):
    """
    Per-output analysis specification. ARS-shaped so the cells in Stage 3
    shells and the operations in Stage 5 ARD generation can join cleanly
    back to this spec.
    """
    spec_id: str                              # "SPEC-001"
    analysis_id: str                          # links to Stage 1 ExtractedAnalysis
    title: str
    output_type: OutputType
    output_category: OutputCategory
    output_number: str                        # "9.3.1"
    output_id: str                            # "t-9.3.1"

    population: str                           # "Safety", "FAS", "PP"
    endpoint: Optional[str] = None
    method: Optional[str] = None
    comparison: Optional[str] = None
    visit_structure: Optional[str] = None
    subgroups: list[str] = Field(default_factory=list)
    output_sub_category: Optional[str] = None  # e.g. "ae", "labs"; from NumberingScheme

    columns: list[TreatmentColumn] = Field(default_factory=list)
    row_groups: list[RowGroup] = Field(default_factory=list)
    statistic_sets: list[StatisticSet] = Field(default_factory=list)
    footnotes: list[str] = Field(default_factory=list)

    applicable_rules: list[str] = Field(default_factory=list)  # Stage 1 rule_ids

    # Provenance: matched vs synthesized
    archetype_id: Optional[str] = None
    archetype_confidence: Optional[float] = None     # 0..1, when matched
    synthesis_basis: Optional[str] = None            # rationale when synthesized
    library_conventions_applied: list[str] = Field(default_factory=list)

    rationale: Optional[str] = None
    review: ReviewState = Field(default_factory=ReviewState)


# --------------------------------------------------------------------- #
# TOC row (one per deliverable output)
# --------------------------------------------------------------------- #

class TocRow(BaseModel):
    row_id: str                               # "ROW-001"
    output_id: str                            # "t-9.3.2.1"
    output_number: str                        # "9.3.2.1"
    output_type: OutputType
    output_category: OutputCategory
    output_sub_category: Optional[str] = None
    title: str
    population: str
    spec_id: str                              # links to AnalysisSpec
    analysis_id: str                          # original Stage 1 analysis
    # (root, cat, sub_or_seq, seq, type) -> sortable even with mixed 3/4-level
    sort_key: tuple[int, int, int, int, str] = Field(
        default_factory=lambda: (0, 0, 0, 0, "")
    )


# --------------------------------------------------------------------- #
# Archetype matching (provider-shaped, see library.py)
# --------------------------------------------------------------------- #

class Archetype(BaseModel):
    """One template from the house mock shell library."""
    archetype_id: str
    name: str
    description: str
    output_type: OutputType
    output_category: OutputCategory
    typical_population: Optional[str] = None
    # Free-text keywords used by the matcher; the real library should
    # also expose row_groups / statistic_sets / footnotes so synthesis
    # can pull them in even when no match qualifies.
    keywords: list[str] = Field(default_factory=list)
    row_groups: list[RowGroup] = Field(default_factory=list)
    statistic_sets: list[StatisticSet] = Field(default_factory=list)
    standard_footnotes: list[str] = Field(default_factory=list)


class ArchetypeMatch(BaseModel):
    archetype_id: str
    confidence: float                          # 0..1
    rationale: str


# --------------------------------------------------------------------- #
# Top-level Stage 2 artifact
# --------------------------------------------------------------------- #

class SynthesisStatus(str, Enum):
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    FAILED = "failed"


class TocSynthesis(BaseModel):
    study_id: str
    sap_extraction_version: int                # Stage 1 input version
    version: int = 1
    status: SynthesisStatus = SynthesisStatus.RUNNING
    numbering_scheme: NumberingScheme = Field(default_factory=NumberingScheme)
    toc: list[TocRow] = Field(default_factory=list)
    specs: list[AnalysisSpec] = Field(default_factory=list)
    progress: dict[str, str] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
