"""
Archetype library access.

The real house mock-shell library is proprietary and lives on a Posit
mount as Word/PDF files. LocalMountArchetypeLibrary (in library_local.py)
reads from there; StubArchetypeLibrary below is a developer fallback when
the mount is not configured.

build_library() picks the right implementation from config + an explicit
version_tag. Different studies can request different library versions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Protocol

from core.config import settings

from .schemas import (
    Archetype, OutputCategory, OutputType,
    RowGroup, StatisticSet,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- #
# Provider interface
# --------------------------------------------------------------------- #

class ArchetypeLibrary(Protocol):
    def list_archetypes(self) -> list[Archetype]: ...
    def get_archetype(self, archetype_id: str) -> Archetype | None: ...
    def list_conventions(self) -> list[str]: ...


def build_library(version_tag: Optional[str] = None) -> "ArchetypeLibrary":
    """
    Factory: prefer the real local-mount library when SHELL_LIBRARY_ROOT is
    configured; otherwise fall back to the stub. Pass a version_tag (the
    version subdirectory name) to override SHELL_LIBRARY_DEFAULT_VERSION.
    """
    root = settings.shell_library_root
    version = version_tag or settings.shell_library_default_version
    if root and version:
        from .library_local import LocalMountArchetypeLibrary
        try:
            return LocalMountArchetypeLibrary(root=root, version=version)
        except FileNotFoundError as exc:
            logger.warning(
                "Configured shell library version not found (%s); falling "
                "back to stub. Set SHELL_LIBRARY_ROOT and "
                "SHELL_LIBRARY_DEFAULT_VERSION, and ensure %s exists.",
                exc, Path(root) / version,
            )
    if root and not version:
        logger.warning(
            "SHELL_LIBRARY_ROOT is set but SHELL_LIBRARY_DEFAULT_VERSION is "
            "not; falling back to stub. Specify a version per study or set "
            "a default."
        )
    return StubArchetypeLibrary()


# --------------------------------------------------------------------- #
# Stub for development
# --------------------------------------------------------------------- #

_CONTINUOUS = StatisticSet(
    set_id="stats_continuous_default",
    name="Continuous summary",
    statistics=["n", "mean", "sd", "median", "min", "max"],
    decimal_precision={"mean": 1, "sd": 2, "median": 1, "min": 0, "max": 0},
)
_CATEGORICAL = StatisticSet(
    set_id="stats_categorical_default",
    name="Categorical summary",
    statistics=["n", "pct"],
    decimal_precision={"pct": 1},
)


_STUB_ARCHETYPES: list[Archetype] = [
    Archetype(
        archetype_id="ARC-DEMOG-001",
        name="Demographics and Baseline Characteristics",
        description=(
            "Standard demographics summary by treatment arm with totals: "
            "age (continuous), sex, race, ethnicity, weight, height, BMI."
        ),
        output_type=OutputType.TABLE,
        output_category=OutputCategory.BASELINE,
        typical_population="Safety",
        keywords=["demographics", "baseline characteristics", "age", "sex", "race"],
        row_groups=[
            RowGroup(group_id="rg_age", label="Age (years)",
                     statistic_set_id="stats_continuous_default", sort_order=1),
            RowGroup(group_id="rg_sex", label="Sex",
                     statistic_set_id="stats_categorical_default", sort_order=2),
            RowGroup(group_id="rg_race", label="Race",
                     statistic_set_id="stats_categorical_default", sort_order=3),
        ],
        statistic_sets=[_CONTINUOUS, _CATEGORICAL],
        standard_footnotes=[
            "Percentages are based on the number of subjects in the safety population.",
            "BMI = weight (kg) / [height (m)]^2.",
        ],
    ),
    Archetype(
        archetype_id="ARC-DISP-001",
        name="Subject Disposition",
        description=(
            "Counts of subjects randomized, treated, completed, and "
            "discontinued, with reasons for discontinuation."
        ),
        output_type=OutputType.TABLE,
        output_category=OutputCategory.BASELINE,
        typical_population="Randomized",
        keywords=["disposition", "discontinuation", "completed", "withdrew", "screen failure"],
        row_groups=[
            RowGroup(group_id="rg_disp_status", label="Disposition status",
                     statistic_set_id="stats_categorical_default", sort_order=1),
            RowGroup(group_id="rg_disp_reason", label="Reason for discontinuation",
                     statistic_set_id="stats_categorical_default", sort_order=2),
        ],
        statistic_sets=[_CATEGORICAL],
        standard_footnotes=[
            "Percentages are based on the number of subjects randomized.",
        ],
    ),
    Archetype(
        archetype_id="ARC-AE-001",
        name="Adverse Events Overview",
        description=(
            "Counts and percentages of subjects with any AE, any TEAE, "
            "any serious AE, any AE leading to discontinuation, deaths."
        ),
        output_type=OutputType.TABLE,
        output_category=OutputCategory.SAFETY,
        typical_population="Safety",
        keywords=["adverse event overview", "TEAE", "serious", "death", "discontinuation"],
        row_groups=[
            RowGroup(group_id="rg_ae_overview", label="Subjects with at least one event",
                     statistic_set_id="stats_categorical_default", sort_order=1),
        ],
        statistic_sets=[_CATEGORICAL],
        standard_footnotes=[
            "Treatment-emergent adverse events are AEs with onset on or after the first dose of study drug.",
            "Subjects are counted once per row regardless of the number of events.",
        ],
    ),
    Archetype(
        archetype_id="ARC-AE-002",
        name="Adverse Events by SOC and Preferred Term",
        description=(
            "AE counts and percentages by MedDRA System Organ Class and "
            "Preferred Term, treatment arm columns with totals."
        ),
        output_type=OutputType.TABLE,
        output_category=OutputCategory.SAFETY,
        typical_population="Safety",
        keywords=["adverse event", "SOC", "preferred term", "PT", "MedDRA", "TEAE"],
        row_groups=[
            RowGroup(group_id="rg_soc", label="System Organ Class",
                     statistic_set_id="stats_categorical_default", sort_order=1),
            RowGroup(group_id="rg_pt", label="Preferred Term",
                     statistic_set_id="stats_categorical_default", sort_order=2),
        ],
        statistic_sets=[_CATEGORICAL],
        standard_footnotes=[
            "MedDRA version <version> coded all adverse events.",
            "Subjects with multiple events in the same SOC/PT are counted once.",
            "Sort order: SOC alphabetical; PT by descending incidence in the total column.",
        ],
    ),
    Archetype(
        archetype_id="ARC-LAB-001",
        name="Laboratory Values - Summary by Visit",
        description=(
            "Mean (SD) and change from baseline for hematology and "
            "clinical chemistry analytes by visit and treatment arm."
        ),
        output_type=OutputType.TABLE,
        output_category=OutputCategory.SAFETY,
        typical_population="Safety",
        keywords=["laboratory", "hematology", "chemistry", "change from baseline", "visit"],
        row_groups=[
            RowGroup(group_id="rg_lab_baseline", label="Baseline",
                     statistic_set_id="stats_continuous_default", sort_order=1),
            RowGroup(group_id="rg_lab_change", label="Change from baseline",
                     statistic_set_id="stats_continuous_default", sort_order=2),
        ],
        statistic_sets=[_CONTINUOUS],
        standard_footnotes=[
            "Baseline is the last non-missing value on or before first dose.",
            "Conventional units are reported.",
        ],
    ),
    Archetype(
        archetype_id="ARC-EFF-001",
        name="Primary Efficacy Analysis - ANCOVA",
        description=(
            "Adjusted means and treatment comparisons from ANCOVA on the "
            "primary efficacy endpoint with LOCF imputation."
        ),
        output_type=OutputType.TABLE,
        output_category=OutputCategory.EFFICACY,
        typical_population="FAS",
        keywords=["primary efficacy", "ANCOVA", "LOCF", "adjusted means", "least squares"],
        row_groups=[
            RowGroup(group_id="rg_eff_summary", label="Endpoint summary",
                     statistic_set_id="stats_continuous_default", sort_order=1),
        ],
        statistic_sets=[_CONTINUOUS],
        standard_footnotes=[
            "ANCOVA model includes treatment, site, and baseline as factors.",
            "Missing values imputed using last observation carried forward (LOCF).",
        ],
    ),
    Archetype(
        archetype_id="ARC-LIST-AE-001",
        name="Listing of Adverse Events",
        description=(
            "Subject-level listing of all adverse events with onset, "
            "duration, severity, relationship, action, and outcome."
        ),
        output_type=OutputType.LISTING,
        output_category=OutputCategory.SAFETY,
        typical_population="Safety",
        keywords=["adverse event listing", "AE listing", "subject-level"],
        row_groups=[],
        statistic_sets=[],
        standard_footnotes=[
            "One row per adverse event; subjects with no events are not listed.",
        ],
    ),
]


_STUB_CONVENTIONS: list[str] = [
    "All continuous variables are summarized with n, mean, SD, median, min, max unless otherwise stated.",
    "Categorical variables are summarized with n and percentage; percentages are based on the analysis population denominator unless noted.",
    "Treatment columns include the column N (subjects in the analysis population) in the header.",
    "A 'Total' column is included for safety summaries by default.",
    "Footnotes are numbered with superscript Arabic numerals; sources of data appear as the last footnote on each output.",
    "Mean and SD are presented with one and two more decimals respectively than the raw data; min and max match raw precision.",
]


class StubArchetypeLibrary:
    """In-memory library for development. Replace with a real provider."""

    def __init__(self,
                 archetypes: list[Archetype] | None = None,
                 conventions: list[str] | None = None):
        self._archetypes = archetypes or _STUB_ARCHETYPES
        self._conventions = conventions or _STUB_CONVENTIONS
        self._by_id = {a.archetype_id: a for a in self._archetypes}

    def list_archetypes(self) -> list[Archetype]:
        return list(self._archetypes)

    def get_archetype(self, archetype_id: str) -> Archetype | None:
        return self._by_id.get(archetype_id)

    def list_conventions(self) -> list[str]:
        return list(self._conventions)
