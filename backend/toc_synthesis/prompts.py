"""
Prompt templates for Stage 2.

Three passes drive synthesis:
  1. Output planner   - decide what physical outputs each Stage 1 analysis
                        produces (table only, table + listing, etc.) and
                        assign category + sequence within scheme.
  2. Archetype match  - classify each output against the house library
                        with a confidence score.
  3. Spec synthesizer - either parameterize the matched archetype or
                        synthesize from SAP + rules, in both cases
                        applying library layout conventions and producing
                        a full AnalysisSpec.

System prompt enforces JSON-only output, citation back to rule ids and
analysis ids, and explicit provenance on every produced spec.
"""

SYSTEM_BASE = """\
You are a senior biostatistician composing analysis specifications for an \
automated TLF generation system. You read approved Stage 1 extractions \
(rules, analyses, gaps) plus a house archetype library, and produce \
fully-specified analysis records.

Hard requirements for every response:
1. Respond with a SINGLE valid JSON object. No prose before or after. No \
markdown code fences.
2. Every produced output records its provenance: archetype_id and \
confidence when matched, synthesis_basis when not.
3. Reference rule ids (R-###) by id, not by paraphrase, when stating \
which rules apply.
4. Reference original analysis ids (A-###) on every spec.
5. Use precise CDISC/ICH terminology where the source materials do.\
"""


# --------------------------------------------------------------------- #
# Pass 1: output planning
# --------------------------------------------------------------------- #

OUTPUT_PLANNER_USER = """\
For each approved Stage 1 analysis below, decide which physical TLF \
outputs are required. Most analyses produce exactly one output (a table); \
some imply a supporting listing or a figure as well. Be specific about \
why each additional output is required.

Output category must be one of: baseline, efficacy, safety, disclosure.
Output type must be one of: T (table), L (listing), F (figure).

Numbering convention for this study:
{numbering_description}

{sub_category_instructions}

Number outputs sequentially within each (root, category[, sub-category]): \
for example, the first table in safety/ae is t-9.3.2.1, the second is \
t-9.3.2.2; the first listing in safety/ae is l-10.3.2.1.

Return JSON:
{{
  "outputs": [
    {{
      "analysis_id": "A-001",
      "output_type": "T",
      "output_category": "safety",
      "output_sub_category": "ae or null",
      "title": "...",
      "rationale": "why this output is needed"
    }}
  ]
}}

APPROVED ANALYSES:
{analyses}

APPLICABLE RULES:
{rules}
"""


# --------------------------------------------------------------------- #
# Pass 2: archetype matching
# --------------------------------------------------------------------- #

ARCHETYPE_MATCH_USER = """\
For each planned output below, identify the best-matching archetype from \
the house library, OR declare no match if the library has no good fit. \
Match policy: prefer a match when one is genuinely close to the planned \
output's content and format; do not stretch a match across categories \
(no labeling a safety output with an efficacy archetype).

Confidence is on [0, 1]:
  >= 0.8 strong match, spec can be largely cloned from archetype
  0.5 - 0.8 partial match, archetype guides structure but spec needs \
adjustment from SAP context
  < 0.5 weak; treat as no match
Use null when no archetype is appropriate.

Return JSON:
{{
  "matches": [
    {{
      "analysis_id": "A-001",
      "output_id": "t-9.3.1",
      "archetype_id": "ARC-AE-002 or null",
      "confidence": 0.92,
      "rationale": "..."
    }}
  ]
}}

PLANNED OUTPUTS:
{outputs}

ARCHETYPE LIBRARY (id, name, type, category, description, keywords):
{archetypes}
"""


# --------------------------------------------------------------------- #
# Pass 3: spec synthesis
# --------------------------------------------------------------------- #

SPEC_SYNTHESIS_USER = """\
For each output below, produce a full analysis specification.

Decision rule (match-preferred):
- If a high-confidence archetype match was provided, START from the \
archetype's row groups, statistic sets, and footnotes; adjust populations, \
treatment columns, and footnotes to fit this study; record \
archetype_id and archetype_confidence on the spec.
- If no match (or weak match), SYNTHESIZE the spec from the SAP analysis \
and the applicable rules. Even in synthesis mode, consult the library \
conventions below for layout, statistic-set defaults, and footnote \
phrasing, and record which conventions you applied in \
library_conventions_applied. Put a short synthesis_basis on the spec.

Statistic set granularity is ROW-GROUP LEVEL: every row group references \
one statistic_set_id, and the spec carries the set of statistic_sets \
referenced. Reuse default sets where appropriate \
(stats_continuous_default, stats_categorical_default); only create new \
sets when the analysis genuinely needs different statistics.

For each spec produce: spec_id (SPEC-###, continue from {next_spec_index}), \
all fields required for ARS-shaped downstream consumption. \
applicable_rules must list only the R-### ids that genuinely constrain \
this analysis.

Treatment columns: derive from the study's treatment arms as named in \
the SAP. Include a Total column for safety summaries unless the rule set \
forbids it. Set show_n=true.

Return JSON:
{{
  "specs": [
    {{
      "spec_id": "SPEC-001",
      "analysis_id": "A-001",
      "title": "...",
      "output_type": "T",
      "output_category": "safety",
      "output_number": "9.3.1",
      "output_id": "t-9.3.1",
      "population": "Safety",
      "endpoint": "...",
      "method": "...",
      "comparison": "...",
      "visit_structure": "...",
      "subgroups": [],
      "columns": [
        {{"column_id": "col_plb", "label": "Placebo", "treatment_code": "PLB", "is_total": false, "show_n": true}}
      ],
      "row_groups": [
        {{"group_id": "rg_soc", "label": "System Organ Class", "statistic_set_id": "stats_categorical_default", "sort_order": 1}}
      ],
      "statistic_sets": [
        {{"set_id": "stats_categorical_default", "name": "Categorical summary", "statistics": ["n", "pct"], "decimal_precision": {{"pct": 1}}}}
      ],
      "footnotes": ["..."],
      "applicable_rules": ["R-003"],
      "archetype_id": "ARC-AE-002 or null",
      "archetype_confidence": 0.92,
      "synthesis_basis": "null if matched; otherwise a sentence",
      "library_conventions_applied": ["convention text snippets"],
      "rationale": "one sentence: what drove this spec"
    }}
  ]
}}

OUTPUTS WITH MATCH RESULTS:
{outputs_with_matches}

STAGE 1 ANALYSES (full detail for synthesis context):
{analyses_detail}

APPLICABLE RULES (full statements):
{rules_detail}

ARCHETYPE DETAILS (for matched archetypes, full row groups / stats / footnotes):
{archetype_details}

LIBRARY CONVENTIONS (consult during synthesis even when no archetype matched):
{conventions}
"""
