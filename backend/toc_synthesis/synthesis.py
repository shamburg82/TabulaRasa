"""
Stage 2 synthesis agent.

Three-pass orchestration:
  1. Output planning  - one or more outputs per Stage 1 analysis
  2. Archetype match  - classify each output against the library
  3. Spec synthesis   - match-preferred: parameterize matched archetypes,
                        synthesize the rest (still consulting library
                        conventions); produce full AnalysisSpec records

Numbering is assigned deterministically in Python after the planner
returns, not by the LLM, so sequence numbers stay strictly monotonic
within each (root, category) and survive re-runs.

Reuses sap_ingestion.llm.BedrockClient as the shared LLM transport (no
new client construction, no enhanced wrappers).
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any, Callable, Optional

from core.llm import BedrockClient

from .library import ArchetypeLibrary
from .prompts import (
    ARCHETYPE_MATCH_USER,
    OUTPUT_PLANNER_USER,
    SPEC_SYNTHESIS_USER,
    SYSTEM_BASE,
)
from .schemas import (
    AnalysisSpec, Archetype, ArchetypeMatch,
    NumberingScheme, OutputCategory, OutputType,
    RowGroup, StatisticSet, TocRow, TreatmentColumn,
)

logger = logging.getLogger(__name__)


# Match-preferred threshold: at or above this confidence, archetype drives
# the spec; below, synthesis takes over while still consulting conventions.
MATCH_THRESHOLD = 0.8


class SynthesisAgent:
    def __init__(
        self,
        library: ArchetypeLibrary,
        llm: Optional[BedrockClient] = None,
        audit_sink: Optional[Callable[[dict], None]] = None,
    ):
        self.library = library
        self.llm = llm or BedrockClient()
        self._audit_sink = audit_sink or (lambda record: None)

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #

    def run(
        self,
        *,
        study_id: str,
        extraction: dict[str, Any],
        scheme: NumberingScheme,
        progress: Optional[Callable[[str, str], None]] = None,
    ) -> dict[str, Any]:
        """
        Drive the three passes. `extraction` is the Stage 1 SapExtraction
        dict (rules + analyses + gaps, post-HITL).
        """
        progress = progress or (lambda name, state: None)

        analyses = [a for a in extraction.get("analyses", [])
                    if a.get("review", {}).get("status") != "rejected"]
        rules = [r for r in extraction.get("rules", [])
                 if r.get("review", {}).get("status") != "rejected"]

        progress("output_planning", "running")
        planned = self._pass_output_planning(analyses, rules, scheme, study_id)
        planned = self._assign_numbering(planned, scheme)
        progress("output_planning", "done")

        progress("archetype_matching", "running")
        matches = self._pass_archetype_matching(planned, study_id)
        progress("archetype_matching", "done")

        progress("spec_synthesis", "running")
        specs = self._pass_spec_synthesis(
            planned=planned, matches=matches, analyses=analyses,
            rules=rules, scheme=scheme, study_id=study_id,
        )
        progress("spec_synthesis", "done")

        toc = self._build_toc(specs)
        return {
            "toc": [row.model_dump() for row in toc],
            "specs": [s.model_dump() for s in specs],
            "numbering_scheme": scheme.model_dump(),
        }

    # ------------------------------------------------------------------ #
    # Pass 1: output planning
    # ------------------------------------------------------------------ #

    def _pass_output_planning(self, analyses, rules, scheme, study_id) -> list[dict]:
        prompt = OUTPUT_PLANNER_USER.format(
            numbering_description=_describe_scheme(scheme),
            sub_category_instructions=_describe_sub_categories(scheme),
            analyses=json.dumps([
                {"analysis_id": a["analysis_id"], "title": a.get("title"),
                 "origin": a.get("origin"), "output_type": a.get("output_type"),
                 "endpoint": a.get("endpoint"), "population": a.get("population"),
                 "method": a.get("method"), "subgroups": a.get("subgroups", []),
                 "convention_basis": a.get("convention_basis")}
                for a in analyses
            ], indent=1),
            rules=json.dumps([
                {"rule_id": r["rule_id"], "statement": r["statement"],
                 "scope": r["scope"], "scope_detail": r.get("scope_detail")}
                for r in rules
            ], indent=1),
        )
        result = self._call(prompt, study_id, action="pass:output_planning")
        return result.get("outputs", [])

    # ------------------------------------------------------------------ #
    # Numbering (deterministic, Python-side)
    # ------------------------------------------------------------------ #

    def _assign_numbering(self, planned: list[dict], scheme: NumberingScheme
                          ) -> list[dict]:
        """Assign output_number + output_id within (root, category[, sub]) groups.

        Sequence counters are keyed by (root, category, sub_category) so a
        scheme with sub_category_map produces strictly monotonic numbering
        within each fourth-level bucket. Outputs without a sub-category in
        a category that has sub-categories defined fall back to a None key,
        getting three-level numbers in their own counter (this lets a
        spec without a sub assignment still receive a clean 9.3.x rather
        than colliding with 9.3.1.x).
        """
        counters: dict[tuple[int, int, Optional[str]], int] = defaultdict(int)
        out: list[dict] = []
        for item in planned:
            try:
                ot = OutputType(item.get("output_type", "T"))
                cat = OutputCategory(item.get("output_category", "safety"))
            except ValueError:
                logger.warning("Skipping output with invalid type/category: %s", item)
                continue
            root = scheme.listing_root if ot == OutputType.LISTING else scheme.table_root
            sub = item.get("output_sub_category")
            # Only honor sub if the scheme defines it for this category.
            valid_subs = scheme.sub_category_map.get(cat.value, {}) or {}
            if sub and sub not in valid_subs:
                logger.warning(
                    "Discarding unknown sub_category '%s' for category '%s'",
                    sub, cat.value,
                )
                sub = None
            counters[(root, scheme.category_map[cat.value], sub)] += 1
            seq = counters[(root, scheme.category_map[cat.value], sub)]
            number = scheme.build_number(ot, cat, seq, sub_category=sub)
            out.append({
                **item,
                "output_type": ot.value,
                "output_category": cat.value,
                "output_sub_category": sub,
                "output_number": number,
                "output_id": scheme.build_output_id(ot, number),
            })
        return out

    # ------------------------------------------------------------------ #
    # Pass 2: archetype matching
    # ------------------------------------------------------------------ #

    def _pass_archetype_matching(self, planned: list[dict], study_id: str
                                 ) -> dict[str, ArchetypeMatch]:
        archetypes = self.library.list_archetypes()
        prompt = ARCHETYPE_MATCH_USER.format(
            outputs=json.dumps([
                {"output_id": p["output_id"], "analysis_id": p["analysis_id"],
                 "output_type": p["output_type"], "output_category": p["output_category"],
                 "title": p.get("title"), "rationale": p.get("rationale")}
                for p in planned
            ], indent=1),
            archetypes=json.dumps([
                {"archetype_id": a.archetype_id, "name": a.name,
                 "output_type": a.output_type.value,
                 "output_category": a.output_category.value,
                 "description": a.description, "keywords": a.keywords}
                for a in archetypes
            ], indent=1),
        )
        result = self._call(prompt, study_id, action="pass:archetype_matching")
        valid_ids = {a.archetype_id for a in archetypes}
        matches: dict[str, ArchetypeMatch] = {}
        for m in result.get("matches", []):
            aid = m.get("archetype_id")
            output_id = m.get("output_id")
            if not output_id:
                continue
            if aid and aid not in valid_ids:
                logger.warning("Discarding match to unknown archetype: %s", aid)
                continue
            if aid is None:
                continue
            matches[output_id] = ArchetypeMatch(
                archetype_id=aid,
                confidence=float(m.get("confidence", 0.0)),
                rationale=m.get("rationale", ""),
            )
        return matches

    # ------------------------------------------------------------------ #
    # Pass 3: spec synthesis
    # ------------------------------------------------------------------ #

    def _pass_spec_synthesis(self, *, planned, matches, analyses, rules,
                             scheme, study_id) -> list[AnalysisSpec]:
        outputs_with_matches = []
        archetype_details: dict[str, Archetype] = {}
        for p in planned:
            m = matches.get(p["output_id"])
            entry = {**p}
            if m:
                entry["match"] = {"archetype_id": m.archetype_id,
                                  "confidence": m.confidence,
                                  "rationale": m.rationale,
                                  "use_archetype_directly": m.confidence >= MATCH_THRESHOLD}
                arc = self.library.get_archetype(m.archetype_id)
                if arc:
                    archetype_details[m.archetype_id] = arc
            else:
                entry["match"] = None
            outputs_with_matches.append(entry)

        analyses_by_id = {a["analysis_id"]: a for a in analyses}
        rules_by_id = {r["rule_id"]: r for r in rules}

        prompt = SPEC_SYNTHESIS_USER.format(
            next_spec_index=1,
            outputs_with_matches=json.dumps(outputs_with_matches, indent=1),
            analyses_detail=json.dumps([
                {"analysis_id": p["analysis_id"], **{
                    k: analyses_by_id.get(p["analysis_id"], {}).get(k)
                    for k in ("title", "endpoint", "population", "method",
                              "comparison", "visit_structure", "subgroups",
                              "applicable_rules", "convention_basis", "rationale")
                }} for p in planned if p["analysis_id"] in analyses_by_id
            ], indent=1),
            rules_detail=json.dumps([
                {"rule_id": r_id, **{k: rules_by_id[r_id].get(k)
                                     for k in ("statement", "scope", "scope_detail", "category")}}
                for r_id in rules_by_id
            ], indent=1),
            archetype_details=json.dumps([
                arc.model_dump() for arc in archetype_details.values()
            ], indent=1),
            conventions="\n".join(f"- {c}" for c in self.library.list_conventions()),
        )
        result = self._call(prompt, study_id, action="pass:spec_synthesis")

        specs: list[AnalysisSpec] = []
        for i, item in enumerate(result.get("specs", []), start=1):
            spec = _to_spec(item, sequence=i, rules_by_id=rules_by_id)
            if spec is not None:
                specs.append(spec)
        # Renumber spec_id deterministically
        for i, spec in enumerate(specs, start=1):
            spec.spec_id = f"SPEC-{i:03d}"
        return specs

    # ------------------------------------------------------------------ #
    # TOC assembly
    # ------------------------------------------------------------------ #

    def _build_toc(self, specs: list[AnalysisSpec]) -> list[TocRow]:
        rows: list[TocRow] = []
        for spec in specs:
            parts = spec.output_number.split(".")
            # Pad to 4 components: (root, cat, sub_or_seq, seq). For
            # 3-level numbers (9.3.1) sub slot is 0 so they sort BEFORE
            # 4-level (9.3.1.x) within the same category.
            nums = [int(p) if p.isdigit() else 0 for p in parts]
            while len(nums) < 4:
                nums.insert(2, 0)
            sort_key = (nums[0], nums[1], nums[2], nums[3], spec.output_type.value)
            rows.append(TocRow(
                row_id=f"ROW-{len(rows) + 1:03d}",
                output_id=spec.output_id,
                output_number=spec.output_number,
                output_type=spec.output_type,
                output_category=spec.output_category,
                output_sub_category=spec.output_sub_category,
                title=spec.title,
                population=spec.population,
                spec_id=spec.spec_id,
                analysis_id=spec.analysis_id,
                sort_key=sort_key,
            ))
        rows.sort(key=lambda r: r.sort_key)
        for i, row in enumerate(rows, start=1):
            row.row_id = f"ROW-{i:03d}"
        return rows

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _call(self, user_prompt: str, study_id: str, *,
              action: str, model_id: Optional[str] = None) -> dict[str, Any]:
        result = self.llm.complete_json(
            system=SYSTEM_BASE, user=user_prompt, model_id=model_id, action=action,
        )
        self._audit_sink({**result.audit, "study_id": study_id, "stage": "stage2_toc"})
        return result.data if isinstance(result.data, dict) else {}


# --------------------------------------------------------------------- #
# Module-level helpers
# --------------------------------------------------------------------- #

def _describe_scheme(scheme: NumberingScheme) -> str:
    figure_note = ("Figures share the table root number." if scheme.figure_shares_table_root
                   else f"Figures use the table root {scheme.table_root}.")
    cats = ", ".join(f"{name}={n}" for name, n in scheme.category_map.items())
    return (
        f"Table root: {scheme.table_root}. Listing root: {scheme.listing_root}. "
        f"{figure_note} Category map ({cats}). "
        f"Output ids use a type prefix: t-, l-, f-."
    )


def _describe_sub_categories(scheme: NumberingScheme) -> str:
    """Render sub-category guidance for the planner prompt."""
    if not scheme.sub_category_map:
        return (
            "This study uses three-level numbering "
            "(root.category.sequence). Set output_sub_category to null on "
            "every output."
        )
    lines = ["Sub-categories are defined for some top categories. Assign "
             "output_sub_category ONLY when the output clearly fits one of "
             "these named buckets; otherwise leave it null and the output "
             "will receive a three-level number within its top category.",
             ""]
    for cat_name, subs in scheme.sub_category_map.items():
        if not subs:
            continue
        ordered = sorted(subs.items(), key=lambda kv: kv[1])
        lines.append(f"  {cat_name}: " + ", ".join(f"{n} ({i})" for n, i in ordered))
    lines.append("")
    lines.append("Top categories without sub-categories listed above use "
                 "three-level numbering as before.")
    return "\n".join(lines)


def _to_spec(item: dict, *, sequence: int,
             rules_by_id: dict[str, dict]) -> Optional[AnalysisSpec]:
    try:
        ot = OutputType(item.get("output_type", "T"))
        cat = OutputCategory(item.get("output_category", "safety"))
    except ValueError:
        logger.warning("Discarding spec with invalid type/category: %s",
                       item.get("spec_id"))
        return None

    columns = [TreatmentColumn(**{k: c.get(k) for k in TreatmentColumn.model_fields})
               for c in (item.get("columns") or []) if isinstance(c, dict)]
    row_groups = [RowGroup(**{k: r.get(k) for k in RowGroup.model_fields})
                  for r in (item.get("row_groups") or []) if isinstance(r, dict)]
    statistic_sets = [StatisticSet(**{k: s.get(k) for k in StatisticSet.model_fields})
                      for s in (item.get("statistic_sets") or []) if isinstance(s, dict)]

    applicable_rules = [rid for rid in (item.get("applicable_rules") or [])
                        if rid in rules_by_id]

    return AnalysisSpec(
        spec_id=item.get("spec_id", f"SPEC-{sequence:03d}"),
        analysis_id=item.get("analysis_id", ""),
        title=item.get("title", ""),
        output_type=ot,
        output_category=cat,
        output_number=item.get("output_number", ""),
        output_id=item.get("output_id", ""),
        population=item.get("population", ""),
        endpoint=item.get("endpoint"),
        method=item.get("method"),
        comparison=item.get("comparison"),
        visit_structure=item.get("visit_structure"),
        subgroups=item.get("subgroups") or [],
        output_sub_category=item.get("output_sub_category"),
        columns=columns,
        row_groups=row_groups,
        statistic_sets=statistic_sets,
        footnotes=item.get("footnotes") or [],
        applicable_rules=applicable_rules,
        archetype_id=item.get("archetype_id"),
        archetype_confidence=item.get("archetype_confidence"),
        synthesis_basis=item.get("synthesis_basis"),
        library_conventions_applied=item.get("library_conventions_applied") or [],
        rationale=item.get("rationale"),
    )
