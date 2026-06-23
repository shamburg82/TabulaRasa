"""
Prompt templates for the five extraction passes.

Conventions enforced across all passes:
  - Output is a single JSON object, no prose, no markdown fences.
  - Every extracted item must cite the SAP section number(s) and page(s)
    it came from, plus a short verbatim quote (<= 25 words) as an anchor
    for the human reviewer.
  - The model never invents content silently: implied analyses and
    proposed defaults must name the convention or standard they rest on.
"""

SYSTEM_BASE = """\
You are a senior biostatistician and clinical statistical programmer working \
inside an automated TLF (Tables, Listings, Figures) generation system for \
clinical study reports. You read Statistical Analysis Plans (SAPs) with the \
rigor of a regulatory reviewer.

Hard requirements for every response:
1. Respond with a SINGLE valid JSON object. No prose before or after. No \
markdown code fences.
2. Every extracted item MUST include citations: the SAP section number, \
section id, page number when available, and a short verbatim quote \
(25 words maximum) anchoring the claim.
3. Do not fabricate. If something is genuinely absent from the provided \
text, it belongs in the gap analysis, not in the extracted items.
4. Use precise CDISC and ICH terminology (FAS, safety population, estimand, \
intercurrent event, TEAE, SOC/PT, etc.) where the SAP uses or implies it.\
"""

# --------------------------------------------------------------------- #
# Pass 1: section map
# --------------------------------------------------------------------- #

SECTION_MAP_USER = """\
Below is the section inventory of a SAP: each entry has a section id, \
heading number, title, and the first portion of its text.

Classify the semantic role(s) of every section. Allowed roles:
{roles}

A section may have multiple roles (e.g., a "Statistical Methods" section \
that also defines populations). Use "other" only when nothing else fits.

Return JSON:
{{
  "section_map": [
    {{"section_id": "...", "number": "...", "title": "...", "roles": ["..."]}}
  ]
}}

SECTION INVENTORY:
{inventory}
"""

# --------------------------------------------------------------------- #
# Pass 2: explicit analyses
# --------------------------------------------------------------------- #

EXPLICIT_ANALYSES_USER = """\
Below are the full texts of SAP sections classified as relevant to planned \
analyses (endpoints, statistical methods, efficacy, safety, subgroups, \
interim analyses).

Extract EVERY analysis explicitly described or enumerated. One record per \
distinct analysis. Where the SAP describes a family (e.g., "summaries of \
each laboratory parameter by visit"), extract it as one analysis with the \
family scope stated in the title rather than expanding per parameter.

For each analysis capture: title; endpoint; population; statistical method; \
treatment comparison; visit structure; subgroups; and whether it is a \
table, listing, or figure if stated or strongly implied.

Number analyses sequentially as A-001, A-002, ... starting from {start_index}.\
Emit a confidence score per item.

Return JSON:
{{
  "analyses": [
    {{
      "analysis_id": "A-001",
      "confidence": "0.00 to 1.00",
      "title": "...",
      "output_type": "T|L|F|null",
      "endpoint": "...",
      "population": "...",
      "method": "...",
      "comparison": "...",
      "visit_structure": "...",
      "subgroups": ["..."],
      "rationale": "one or two sentences on why this was extracted",
      "citations": [{{"section_number": "...", "section_id": "...", "page": 0, "quote": "..."}}]
    }}
  ]
}}

SAP SECTIONS:
{sections}
"""

# --------------------------------------------------------------------- #
# Pass 3: rules
# --------------------------------------------------------------------- #

RULE_EXTRACTION_USER = """\
Below are full texts of SAP sections likely to contain cross-cutting rules: \
analysis populations, treatment assignment conventions, missing data \
handling, multiplicity, baseline definitions, visit windowing, AE \
definitions, rounding/precision conventions, and general presentation rules.

Extract every RULE: a statement that constrains how multiple analyses must \
be performed or presented. Examples of rule categories: \
treatment_assignment (e.g., planned treatment for efficacy, actual for \
safety), population (which population applies where), baseline_definition, \
missing_data, visit_windowing, multiplicity, precision_rounding, \
ae_handling, presentation, derivation.

For each rule, assign a scope:
- global: applies to all analyses
- safety_only / efficacy_only
- domain_specific (state the domain in scope_detail, e.g., "labs")
- population_specific (state the population in scope_detail)

Number rules sequentially as R-001, R-002, ... Normalize the statement into \
a single clear sentence in your own words; the verbatim text goes in the \
citation quote. Emit a confidence score per item.

Return JSON:
{{
  "rules": [
    {{
      "rule_id": "R-001",
      "confidence": "0.00 to 1.00",
      "statement": "...",
      "scope": "global|safety_only|efficacy_only|domain_specific|population_specific",
      "scope_detail": "... or null",
      "category": "...",
      "rationale": "...",
      "citations": [{{"section_number": "...", "section_id": "...", "page": 0, "quote": "..."}}]
    }}
  ]
}}

SAP SECTIONS:
{sections}
"""

# --------------------------------------------------------------------- #
# Pass 4: implicit analyses
# --------------------------------------------------------------------- #

IMPLICIT_ANALYSES_USER = """\
You are given:
1. The SAP section map (titles and roles).
2. The list of EXPLICIT analyses already extracted.
3. House standard conventions (may be empty).

Identify analyses that are IMPLIED but not explicitly enumerated. Sources \
of implication, in priority order:
- ICH E3 expectations for a CSR (e.g., subject disposition, demographics \
and baseline characteristics, protocol deviations, exposure, AE overview, \
SAE summaries, deaths, discontinuations due to AEs, standard lab/vitals/ECG \
summaries when those domains are collected).
- Statements in the SAP that commit to compliance with a guideline or \
standard without enumerating the resulting outputs.
- House standards provided below.
- Internal consistency (e.g., an efficacy table implies a supporting \
listing where the SAP says all tables are supported by listings).

Do NOT duplicate any explicit analysis. For each implied analysis, state \
the convention_basis: exactly which convention, guideline reference, SAP \
commitment, or house standard implies it.

Continue numbering from A-{start_index:03d}.

Return JSON with the same analysis record shape as before, plus \
"convention_basis" on each record:
{{ "analyses": [ ... ] }}

SECTION MAP:
{section_map}

EXPLICIT ANALYSES (titles only):
{explicit_titles}

HOUSE STANDARDS:
{house_standards}
"""

# --------------------------------------------------------------------- #
# Pass 5: gaps
# --------------------------------------------------------------------- #

GAP_ANALYSIS_USER = """\
You are given the SAP section map, the extracted rules, the extracted \
analyses (explicit and implied), and house standard defaults (may be empty).

Identify GAPS: information a statistical programming team needs to produce \
the TLFs but which the SAP does not specify, judged against ICH E3/E9 \
expectations and the house defaults. Typical gap areas: decimal precision \
conventions, handling of partial dates, baseline definition for specific \
domains, treatment-emergent window definition, ordering/sorting rules, \
denominator conventions, pooling of sites, handling of retests/unscheduled \
visits, footnote conventions.

For each gap, propose a default when one exists in the house standards or \
common convention, and name its source ("house_standard:<id>" or \
"convention:<reference>"). If no defensible default exists, set \
proposed_default to null and say what decision is needed. Emit a \
confidence score per item.

Number gaps G-001, G-002, ...

Return JSON:
{{
  "gaps": [
    {{
      "gap_id": "G-001",
      "confidence": "0.00 to 1.00",
      "description": "...",
      "affected_area": "...",
      "proposed_default": "... or null",
      "default_source": "... or null",
      "rationale": "...",
      "citations": [{{"section_number": "...", "section_id": "...", "page": 0, "quote": "..."}}]
    }}
  ]
}}

SECTION MAP:
{section_map}

RULES:
{rules}

ANALYSES (titles + origin):
{analyses}

HOUSE STANDARD DEFAULTS:
{house_standards}
"""

# --------------------------------------------------------------------- #
# Rule linking (post-pass, light model)
# --------------------------------------------------------------------- #

RULE_LINKING_USER = """\
Given the list of rules and the list of analyses below, return for each \
analysis the rule ids that apply to it, based on each rule's scope and the \
analysis's population/domain/safety-vs-efficacy character.

Return JSON:
{{ "links": [ {{"analysis_id": "A-001", "rule_ids": ["R-001", "R-004"]}} ] }}

RULES:
{rules}

ANALYSES:
{analyses}
"""
