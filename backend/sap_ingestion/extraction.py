"""
Multi-pass SAP extraction agent (Stage 1 core).

Pass order matters: the section map drives which sections feed the later
passes; rules are extracted before implicit analyses so convention
reasoning can see them; gaps run last with full visibility of everything
extracted. A final light-model pass links rules to analyses so a rule
correction in HITL review propagates to every affected analysis.

Long SAPs are handled by batching sections under a character budget per
call; item ids are renumbered globally after each pass so A-/R-/G- ids
stay sequential regardless of batching.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Iterable, Optional

from core.config import settings
from core.llm import BedrockClient
from .prompts import (
    EXPLICIT_ANALYSES_USER,
    GAP_ANALYSIS_USER,
    IMPLICIT_ANALYSES_USER,
    RULE_EXTRACTION_USER,
    RULE_LINKING_USER,
    SECTION_MAP_USER,
    SYSTEM_BASE,
)
from .schemas import (
    AnalysisOrigin,
    Citation,
    DocumentSection,
    ExtractedAnalysis,
    ExtractedRule,
    IdentifiedGap,
    SectionMapEntry,
    SectionRole,
)

logger = logging.getLogger(__name__)

# Which section roles feed which pass
_ANALYSIS_ROLES = {
    SectionRole.OBJECTIVES, SectionRole.ENDPOINTS, SectionRole.STATISTICAL_METHODS,
    SectionRole.SAFETY, SectionRole.EFFICACY, SectionRole.SUBGROUPS,
    SectionRole.INTERIM, SectionRole.MULTIPLICITY,
}
_RULE_ROLES = {
    SectionRole.POPULATIONS, SectionRole.STATISTICAL_METHODS, SectionRole.MISSING_DATA,
    SectionRole.MULTIPLICITY, SectionRole.AE_DEFINITIONS, SectionRole.VISITS,
    SectionRole.DERIVATIONS, SectionRole.SAFETY, SectionRole.EFFICACY,
}


class ExtractionAgent:
    def __init__(self, llm: Optional[BedrockClient] = None,
                 audit_sink: Optional[Callable[[dict], None]] = None):
        self.llm = llm or BedrockClient()
        self._audit_sink = audit_sink or (lambda record: None)

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    def run(
        self,
        sections: list[DocumentSection],
        *,
        study_id: str,
        house_standards: str = "",
        progress: Optional[Callable[[str, str], None]] = None,
    ) -> dict[str, Any]:
        progress = progress or (lambda name, state: None)

        progress("section_map", "running")
        section_map = self._pass_section_map(sections, study_id)
        progress("section_map", "done")

        progress("explicit_analyses", "running")
        explicit = self._pass_explicit_analyses(sections, section_map, study_id)
        progress("explicit_analyses", "done")

        progress("rule_extraction", "running")
        rules = self._pass_rules(sections, section_map, study_id)
        progress("rule_extraction", "done")

        progress("implicit_analyses", "running")
        implied = self._pass_implicit_analyses(
            section_map, explicit, house_standards, study_id, start_index=len(explicit) + 1
        )
        progress("implicit_analyses", "done")

        analyses = explicit + implied

        progress("gap_analysis", "running")
        gaps = self._pass_gaps(section_map, rules, analyses, house_standards, study_id)
        progress("gap_analysis", "done")

        progress("rule_linking", "running")
        self._link_rules(rules, analyses, study_id)
        progress("rule_linking", "done")

        return {
            "section_map": [s.model_dump() for s in section_map],
            "rules": [r.model_dump() for r in rules],
            "analyses": [a.model_dump() for a in analyses],
            "gaps": [g.model_dump() for g in gaps],
        }

    # ------------------------------------------------------------------ #
    # Pass 1: section map
    # ------------------------------------------------------------------ #

    def _pass_section_map(self, sections, study_id) -> list[SectionMapEntry]:
        inventory_lines = [
            f"[{s.section_id}] {s.number or '-'} | {s.title} | "
            f"pages {s.page_start}-{s.page_end} | {s.text[:300].replace(chr(10), ' ')}"
            for s in sections
        ]
        entries: list[SectionMapEntry] = []
        for batch in _batch_lines(inventory_lines, settings.pass_char_budget):
            prompt = SECTION_MAP_USER.format(
                roles=", ".join(r.value for r in SectionRole),
                inventory="\n".join(batch),
            )
            result = self._call(prompt, study_id, action="pass:section_map")
            for item in result.get("section_map", []):
                roles = [SectionRole(r) for r in item.get("roles", []) if _valid_role(r)]
                entries.append(SectionMapEntry(
                    section_id=item["section_id"],
                    number=item.get("number"),
                    title=item.get("title", ""),
                    roles=roles or [SectionRole.OTHER],
                ))
        return entries

    # ------------------------------------------------------------------ #
    # Pass 2: explicit analyses
    # ------------------------------------------------------------------ #

    def _pass_explicit_analyses(self, sections, section_map, study_id) -> list[ExtractedAnalysis]:
        relevant = _sections_for_roles(sections, section_map, _ANALYSIS_ROLES)
        analyses: list[ExtractedAnalysis] = []
        for batch in _batch_sections(relevant, settings.pass_char_budget):
            prompt = EXPLICIT_ANALYSES_USER.format(
                start_index=f"A-{len(analyses) + 1:03d}",
                sections=_render_sections(batch),
            )
            result = self._call(prompt, study_id, action="pass:explicit_analyses")
            for item in result.get("analyses", []):
                analyses.append(_to_analysis(item, AnalysisOrigin.EXPLICIT))
        return _renumber(analyses, "analysis_id", "A")

    # ------------------------------------------------------------------ #
    # Pass 3: rules
    # ------------------------------------------------------------------ #

    def _pass_rules(self, sections, section_map, study_id) -> list[ExtractedRule]:
        relevant = _sections_for_roles(sections, section_map, _RULE_ROLES)
        rules: list[ExtractedRule] = []
        for batch in _batch_sections(relevant, settings.pass_char_budget):
            prompt = RULE_EXTRACTION_USER.format(sections=_render_sections(batch))
            result = self._call(prompt, study_id, action="pass:rule_extraction")
            for item in result.get("rules", []):
                rules.append(ExtractedRule(
                    rule_id=item.get("rule_id", "R-000"),
                    statement=item.get("statement", ""),
                    scope=item.get("scope", "global"),
                    scope_detail=item.get("scope_detail"),
                    category=item.get("category", "uncategorized"),
                    rationale=item.get("rationale"),
                    citations=_citations(item),
                ))
        return _renumber(rules, "rule_id", "R")

    # ------------------------------------------------------------------ #
    # Pass 4: implicit analyses
    # ------------------------------------------------------------------ #

    def _pass_implicit_analyses(
        self, section_map, explicit, house_standards, study_id, *, start_index: int
    ) -> list[ExtractedAnalysis]:
        prompt = IMPLICIT_ANALYSES_USER.format(
            start_index=start_index,
            section_map=json.dumps(
                [{"number": s.number, "title": s.title, "roles": [r.value for r in s.roles]}
                 for s in section_map], indent=1),
            explicit_titles=json.dumps([a.title for a in explicit], indent=1),
            house_standards=house_standards or "(none provided)",
        )
        result = self._call(prompt, study_id, action="pass:implicit_analyses")
        implied = [_to_analysis(item, AnalysisOrigin.IMPLIED)
                   for item in result.get("analyses", [])]
        # Renumber continuing after the explicit block
        for offset, a in enumerate(implied):
            a.analysis_id = f"A-{start_index + offset:03d}"
        return implied

    # ------------------------------------------------------------------ #
    # Pass 5: gaps
    # ------------------------------------------------------------------ #

    def _pass_gaps(self, section_map, rules, analyses, house_standards, study_id
                   ) -> list[IdentifiedGap]:
        prompt = GAP_ANALYSIS_USER.format(
            section_map=json.dumps(
                [{"number": s.number, "title": s.title} for s in section_map], indent=1),
            rules=json.dumps(
                [{"rule_id": r.rule_id, "statement": r.statement, "scope": r.scope.value}
                 for r in rules], indent=1),
            analyses=json.dumps(
                [{"analysis_id": a.analysis_id, "title": a.title, "origin": a.origin.value}
                 for a in analyses], indent=1),
            house_standards=house_standards or "(none provided)",
        )
        result = self._call(prompt, study_id, action="pass:gap_analysis")
        gaps = [IdentifiedGap(
            gap_id=item.get("gap_id", "G-000"),
            description=item.get("description", ""),
            affected_area=item.get("affected_area", ""),
            proposed_default=item.get("proposed_default"),
            default_source=item.get("default_source"),
            rationale=item.get("rationale"),
            citations=_citations(item),
        ) for item in result.get("gaps", [])]
        return _renumber(gaps, "gap_id", "G")

    # ------------------------------------------------------------------ #
    # Post-pass: rule -> analysis linking (light model)
    # ------------------------------------------------------------------ #

    def _link_rules(self, rules, analyses, study_id) -> None:
        if not rules or not analyses:
            return
        prompt = RULE_LINKING_USER.format(
            rules=json.dumps(
                [{"rule_id": r.rule_id, "statement": r.statement,
                  "scope": r.scope.value, "scope_detail": r.scope_detail}
                 for r in rules], indent=1),
            analyses=json.dumps(
                [{"analysis_id": a.analysis_id, "title": a.title,
                  "population": a.population, "endpoint": a.endpoint}
                 for a in analyses], indent=1),
        )
        result = self._call(prompt, study_id, action="pass:rule_linking",
                            model_id=settings.model_light)
        by_id = {a.analysis_id: a for a in analyses}
        valid_rules = {r.rule_id for r in rules}
        for link in result.get("links", []):
            analysis = by_id.get(link.get("analysis_id"))
            if analysis:
                analysis.applicable_rules = [
                    rid for rid in link.get("rule_ids", []) if rid in valid_rules
                ]

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _call(self, user_prompt: str, study_id: str, *, action: str,
              model_id: Optional[str] = None) -> dict[str, Any]:
        result = self.llm.complete_json(
            system=SYSTEM_BASE, user=user_prompt, model_id=model_id, action=action
        )
        self._audit_sink({**result.audit, "study_id": study_id, "stage": "stage1_ingestion"})
        return result.data if isinstance(result.data, dict) else {}


# ---------------------------------------------------------------------- #
# Module-level helpers
# ---------------------------------------------------------------------- #

def _valid_role(value: str) -> bool:
    try:
        SectionRole(value)
        return True
    except ValueError:
        return False


def _sections_for_roles(sections, section_map, roles: set[SectionRole]
                        ) -> list[DocumentSection]:
    wanted = {e.section_id for e in section_map if set(e.roles) & roles}
    selected = [s for s in sections if s.section_id in wanted and s.text]
    # Fallback: if role mapping was too sparse, use all non-trivial sections.
    return selected or [s for s in sections if s.char_count > 200]


def _render_sections(sections: Iterable[DocumentSection]) -> str:
    parts = []
    for s in sections:
        parts.append(
            f"--- [{s.section_id}] {s.number or ''} {s.title} "
            f"(pages {s.page_start}-{s.page_end}) ---\n{s.text}"
        )
    return "\n\n".join(parts)


def _batch_sections(sections: list[DocumentSection], budget: int
                    ) -> Iterable[list[DocumentSection]]:
    batch, size = [], 0
    for s in sections:
        cost = s.char_count + 200
        if batch and size + cost > budget:
            yield batch
            batch, size = [], 0
        batch.append(s)
        size += cost
    if batch:
        yield batch


def _batch_lines(lines: list[str], budget: int) -> Iterable[list[str]]:
    batch, size = [], 0
    for line in lines:
        if batch and size + len(line) > budget:
            yield batch
            batch, size = [], 0
        batch.append(line)
        size += len(line)
    if batch:
        yield batch


def _citations(item: dict) -> list[Citation]:
    return [Citation(**{k: c.get(k) for k in Citation.model_fields})
            for c in item.get("citations", []) if isinstance(c, dict)]


def _to_analysis(item: dict, origin: AnalysisOrigin) -> ExtractedAnalysis:
    return ExtractedAnalysis(
        analysis_id=item.get("analysis_id", "A-000"),
        origin=origin,
        title=item.get("title", ""),
        output_type=item.get("output_type"),
        endpoint=item.get("endpoint"),
        population=item.get("population"),
        method=item.get("method"),
        comparison=item.get("comparison"),
        visit_structure=item.get("visit_structure"),
        subgroups=item.get("subgroups") or [],
        convention_basis=item.get("convention_basis"),
        rationale=item.get("rationale"),
        citations=_citations(item),
    )


def _renumber(items: list, id_field: str, prefix: str) -> list:
    """Make ids globally sequential after batched passes."""
    for i, item in enumerate(items, start=1):
        setattr(item, id_field, f"{prefix}-{i:03d}")
    return items
