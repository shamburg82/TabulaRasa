/**
 * In-memory mock for Stage 1 + Studies, matching the actual backend contract.
 * Set VITE_USE_MOCK=true to drive the UI without a running backend.
 */

const SECTION_MAP = [
  { section_id: 's_0001', number: '1', title: 'Introduction', roles: ['administrative'] },
  { section_id: 's_0002', number: '2', title: 'Study Objectives', roles: ['objectives_estimands'] },
  { section_id: 's_0003', number: '3', title: 'Study Design', roles: ['administrative'] },
  { section_id: 's_0004', number: '3.2', title: 'Treatment Assignment', roles: ['administrative'] },
  { section_id: 's_0005', number: '4', title: 'Analysis Populations', roles: ['analysis_populations'] },
  { section_id: 's_0006', number: '5', title: 'General Statistical Considerations', roles: ['statistical_methods'] },
  { section_id: 's_0007', number: '5.1', title: 'Populations Used for Analysis', roles: ['analysis_populations'] },
  { section_id: 's_0008', number: '6', title: 'Efficacy Analyses', roles: ['efficacy_analyses', 'endpoints'] },
  { section_id: 's_0009', number: '6.2.1', title: 'Primary Efficacy Endpoint', roles: ['endpoints', 'statistical_methods'] },
  { section_id: 's_0010', number: '7', title: 'Safety Analyses', roles: ['safety_analyses'] },
  { section_id: 's_0011', number: '7.3', title: 'Adverse Events', roles: ['safety_analyses', 'ae_definitions'] },
  { section_id: 's_0012', number: 'Appx A', title: 'Visit Windows', roles: ['visit_windows'] },
  { section_id: 's_0013', number: 'Appx B', title: 'Derived Variables', roles: ['derived_variables'] },
];

const RULES = [
  { rule_id: 'R-001', confidence: 0.96, statement: 'Use planned treatment for efficacy analyses; actual treatment received for safety analyses.', scope: 'global', scope_detail: null, category: 'treatment_assignment', citations: [{ section_number: '3.2', section_title: 'Treatment Assignment', section_id: 's_0004', page: 18, quote: 'Efficacy analyses will use the planned treatment assignment.' }, { section_number: '5.1', section_title: 'Populations Used for Analysis', section_id: 's_0007', page: 41, quote: 'Safety analyses will use the actual treatment received.' }], rationale: 'Two passages independently confirm this rule. Cross-referenced against ICH E9 for consistency.', review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { rule_id: 'R-002', confidence: 0.93, statement: 'Adverse events coded with MedDRA v26.1. AESI defined per Protocol Appendix C.', scope: 'safety_only', scope_detail: null, category: 'coding_dictionary', citations: [{ section_number: '7.3', section_title: 'Adverse Events', section_id: 's_0011', page: 102, quote: 'AEs will be coded using MedDRA version 26.1.' }], rationale: 'Single explicit statement at the start of the AE analysis section.', review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { rule_id: 'R-003', confidence: 0.71, statement: 'Decimal precision: 1 decimal for means, 2 for SDs.', scope: 'global', scope_detail: null, category: 'display_format', citations: [], rationale: 'SAP does not specify; applied house default per SOP-BIO-014.', review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { rule_id: 'R-004', confidence: 0.98, statement: 'Safety analyses use the Safety Population; efficacy analyses use the FAS with PP sensitivity.', scope: 'global', scope_detail: null, category: 'population', citations: [{ section_number: '4', section_title: 'Analysis Populations', section_id: 's_0005', page: 23, quote: null }], rationale: 'Standard population assignments confirmed in §4.', review: { status: 'accepted', reviewer: 'R. Chen', reviewed_at: '2026-05-15T14:40:00Z', reason: null, edited_value: null } },
  { rule_id: 'R-005', confidence: 0.97, statement: 'Primary endpoint analyzed using MMRM with unstructured covariance and Kenward-Roger denominator df.', scope: 'efficacy_only', scope_detail: 'primary endpoint only', category: 'statistical_method', citations: [{ section_number: '6.2.1', section_title: 'Primary Efficacy Endpoint', section_id: 's_0009', page: 58, quote: 'A mixed model for repeated measures (MMRM) will be fit...' }], rationale: 'Explicit method specification.', review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { rule_id: 'R-006', confidence: 0.84, statement: 'ICH E3 §12 mandates AE overview, AEs by SOC/PT, SAEs, and AEs leading to discontinuation summaries.', scope: 'safety_only', scope_detail: null, category: 'required_outputs', citations: [], rationale: 'Implied by ICH E3 compliance language in §1.2.', review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { rule_id: 'R-007', confidence: 0.68, statement: 'Treatment column ordering: Placebo > Low Dose > High Dose > Total.', scope: 'global', scope_detail: null, category: 'display_format', citations: [], rationale: 'Column ordering not specified; applied house default.', review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
];

const ANALYSES = [
  { analysis_id: 'A-001', confidence: 0.94, origin: 'explicit', title: 'Demographics and Baseline Characteristics', output_type: 'T', endpoint: 'Demographic variables', population: 'Safety', method: 'Descriptive', comparison: null, visit_structure: 'Baseline only', subgroups: [], applicable_rules: ['R-001', 'R-004', 'R-007'], convention_basis: null, citations: [{ section_number: '5.2', section_title: null, section_id: null, page: 43, quote: null }], rationale: null, review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { analysis_id: 'A-002', confidence: 0.91, origin: 'explicit', title: 'Disposition of Subjects', output_type: 'T', endpoint: 'Disposition status', population: 'All Enrolled', method: 'Descriptive', comparison: null, visit_structure: null, subgroups: [], applicable_rules: ['R-004'], convention_basis: null, citations: [{ section_number: '5.3', section_title: null, section_id: null, page: 45, quote: null }], rationale: null, review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { analysis_id: 'A-003', confidence: 0.97, origin: 'explicit', title: 'Primary Efficacy - Change from Baseline in HbA1c at Week 24', output_type: 'T', endpoint: 'Change in HbA1c', population: 'FAS', method: 'MMRM, unstructured covariance, KR df', comparison: 'Each active arm vs placebo', visit_structure: 'Weeks 4, 8, 12, 16, 20, 24', subgroups: [], applicable_rules: ['R-001', 'R-005'], convention_basis: null, citations: [{ section_number: '6.2.1', section_title: 'Primary Efficacy Endpoint', section_id: 's_0009', page: 58, quote: null }], rationale: null, review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { analysis_id: 'A-004', confidence: 0.86, origin: 'implied', title: 'Overview of Adverse Events', output_type: 'T', endpoint: 'AE summary categories', population: 'Safety', method: 'Descriptive: n (%)', comparison: null, visit_structure: null, subgroups: [], applicable_rules: ['R-001', 'R-002', 'R-004', 'R-006'], convention_basis: 'ICH E3 §12.2.1', citations: [], rationale: 'Required by ICH E3 §12. Not explicitly enumerated in SAP but mandatory for CSR.', review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { analysis_id: 'A-005', confidence: 0.93, origin: 'explicit', title: 'Adverse Events by System Organ Class and Preferred Term', output_type: 'T', endpoint: 'AE counts by SOC and PT', population: 'Safety', method: 'Descriptive: n (%) per arm', comparison: null, visit_structure: null, subgroups: [], applicable_rules: ['R-001', 'R-002', 'R-004', 'R-007'], convention_basis: null, citations: [{ section_number: '7.3.2', section_title: null, section_id: 's_0011', page: 108, quote: null }], rationale: null, review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { analysis_id: 'A-006', confidence: 0.81, origin: 'implied', title: 'Listing of Subjects with Serious AEs', output_type: 'L', endpoint: null, population: 'Safety', method: 'Subject listing', comparison: null, visit_structure: null, subgroups: [], applicable_rules: [], convention_basis: 'ICH E3 §16.2.7', citations: [], rationale: 'Standard listing required by ICH E3.', review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
];

const GAPS = [
  { gap_id: 'G-001', confidence: 0.78, description: 'Decimal precision not specified for continuous endpoints.', affected_area: 'Display formatting across all continuous summaries', proposed_default: '1 decimal for means, 2 for SDs, 0 for min/max, 1 for percentages', default_source: 'SOP-BIO-014', rationale: 'Standard house formatting per SOP-BIO-014. Drives R-003.', citations: [], review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
  { gap_id: 'G-002', confidence: 0.65, description: 'Treatment column ordering not specified.', affected_area: 'All multi-arm tables', proposed_default: 'Placebo > Low Dose > High Dose > Total', default_source: 'House default', rationale: 'Standard ordering (control first, ascending dose, total last).', citations: [], review: { status: 'pending', reviewer: null, reviewed_at: null, reason: null, edited_value: null } },
];

const AUDIT = [
  { study_id: 'ABC-301', stage: 'stage1_ingestion', action: 'pass:section_map', model_id: 'claude-opus-4-7', temperature: 0.0, prompt_sha256: 'a3f...', response_sha256: '7d2...', input_tokens: 48210, output_tokens: 3120, latency_ms: 28400, created_at: '2026-05-15T14:33:12Z' },
  { study_id: 'ABC-301', stage: 'stage1_ingestion', action: 'pass:explicit_analyses', model_id: 'claude-opus-4-7', temperature: 0.0, prompt_sha256: 'b1c...', response_sha256: '4e8...', input_tokens: 52100, output_tokens: 4820, latency_ms: 41200, created_at: '2026-05-15T14:34:01Z' },
  { study_id: 'ABC-301', stage: 'stage1_ingestion', action: 'pass:rules', model_id: 'claude-opus-4-7', temperature: 0.0, prompt_sha256: 'c9d...', response_sha256: '1f3...', input_tokens: 58400, output_tokens: 5210, latency_ms: 47800, created_at: '2026-05-15T14:35:18Z' },
  { study_id: 'ABC-301', stage: 'stage1_ingestion', action: 'pass:implied_analyses', model_id: 'claude-opus-4-7', temperature: 0.0, prompt_sha256: 'd2e...', response_sha256: '8a4...', input_tokens: 61200, output_tokens: 2840, latency_ms: 35100, created_at: '2026-05-15T14:36:42Z' },
  { study_id: 'ABC-301', stage: 'stage1_ingestion', action: 'pass:gaps', model_id: 'claude-opus-4-7', temperature: 0.0, prompt_sha256: 'e4f...', response_sha256: '5c7...', input_tokens: 64612, output_tokens: 2432, latency_ms: 33000, created_at: '2026-05-15T14:38:05Z' },
];

// Mutable in-memory store
const STATE = {
  studies: {
    'ABC-301': {
      study_id: 'ABC-301',
      sap_document_id: 'doc_abc301_sap_v2_1',
      version: 1,
      status: 'awaiting_review',
      section_map: SECTION_MAP,
      rules: structuredClone(RULES),
      analyses: structuredClone(ANALYSES),
      gaps: structuredClone(GAPS),
      pass_progress: { section_map: 'done', explicit_analyses: 'done', rules: 'done', implied_analyses: 'done', gaps: 'done' },
      error: null,
      created_at: '2026-05-15T14:32:00Z',
      updated_at: '2026-05-15T14:38:05Z',
    },
    'XYZ-204': {
      study_id: 'XYZ-204',
      sap_document_id: 'doc_xyz204_sap_v1_0',
      version: 1,
      status: 'approved',
      section_map: SECTION_MAP.slice(0, 8),
      rules: structuredClone(RULES.slice(0, 4)).map(r => ({ ...r, review: { status: 'accepted', reviewer: 'M. Okafor', reviewed_at: '2026-04-22T11:00:00Z', reason: null, edited_value: null } })),
      analyses: structuredClone(ANALYSES.slice(0, 3)).map(a => ({ ...a, review: { status: 'accepted', reviewer: 'M. Okafor', reviewed_at: '2026-04-22T11:00:00Z', reason: null, edited_value: null } })),
      gaps: [],
      pass_progress: { section_map: 'done', explicit_analyses: 'done', rules: 'done', implied_analyses: 'done', gaps: 'done' },
      error: null,
      created_at: '2026-04-20T09:00:00Z',
      updated_at: '2026-04-22T11:05:00Z',
    },
  },
  audit: {
    'ABC-301': structuredClone(AUDIT),
    'XYZ-204': [],
  },
};

const delay = (ms = 200) => new Promise((r) => setTimeout(r, ms));

export async function listStudies() {
  await delay();
  return Object.values(STATE.studies).map((s) => ({
    study_id: s.study_id,
    version: s.version,
    status: s.status,
    updated_at: s.updated_at,
    created_at: s.created_at,
    sap_document_id: s.sap_document_id,
    rules_count: s.rules.length,
    analyses_count: s.analyses.length,
    gaps_count: s.gaps.length,
  }));
}

export async function getExtraction(studyId) {
  await delay();
  const ext = STATE.studies[studyId];
  if (!ext) {
    const err = new Error(`No extraction found for study ${studyId}`);
    err.status = 404;
    throw err;
  }
  return structuredClone(ext);
}

export async function getAudit(studyId) {
  await delay();
  return structuredClone(STATE.audit[studyId] || []);
}

export async function uploadSap(studyId, { file, versionTag, houseStandards }) {
  await delay(400);
  // Simulate a fresh extraction kicking off
  STATE.studies[studyId] = {
    study_id: studyId,
    sap_document_id: `doc_${studyId.toLowerCase()}_${Date.now()}`,
    version: (STATE.studies[studyId]?.version || 0) + 1,
    status: 'running',
    section_map: [],
    rules: [],
    analyses: [],
    gaps: [],
    pass_progress: {},
    error: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  STATE.audit[studyId] = [];

  // Simulate the 5 passes completing over time
  const passes = ['section_map', 'explicit_analyses', 'rules', 'implied_analyses', 'gaps'];
  passes.forEach((p, i) => {
    setTimeout(() => {
      const s = STATE.studies[studyId];
      if (!s) return;
      s.pass_progress[p] = 'done';
      s.updated_at = new Date().toISOString();
      if (i === passes.length - 1) {
        s.section_map = SECTION_MAP;
        s.rules = structuredClone(RULES);
        s.analyses = structuredClone(ANALYSES);
        s.gaps = structuredClone(GAPS);
        s.status = 'awaiting_review';
        STATE.audit[studyId] = structuredClone(AUDIT).map((a) => ({ ...a, study_id: studyId }));
      }
    }, (i + 1) * 1500);
  });

  return { study_id: studyId, status: 'accepted', detail: 'Extraction started.' };
}

export async function postReview(studyId, version, itemKind, itemId, payload) {
  await delay(80);
  const ext = STATE.studies[studyId];
  if (!ext) throw new Error('Study not found');
  const idField = itemKind === 'rules' ? 'rule_id' : itemKind === 'analyses' ? 'analysis_id' : 'gap_id';
  const target = ext[itemKind].find((x) => x[idField] === itemId);
  if (!target) throw new Error(`Item not found: ${itemId}`);
  target.review = {
    ...target.review,
    ...payload,
    reviewed_at: new Date().toISOString(),
  };
  ext.updated_at = new Date().toISOString();
  return structuredClone(target);
}

export async function postApprove(studyId, version, reviewer) {
  await delay();
  const ext = STATE.studies[studyId];
  if (!ext) throw new Error('Study not found');
  ext.status = 'approved';
  ext.updated_at = new Date().toISOString();
  return structuredClone(ext);
}

export async function uploadReference() { await delay(300); return { status: 'ok' }; }
export async function search() { await delay(); return { results: [] }; }

// --- additions for v2 ---

export async function postUserRule(studyId, version, body) {
  await delay(120);
  const ext = STATE.studies[studyId];
  if (!ext) throw new Error('Study not found');
  const seq = ext.rules.filter((r) => r.rule_id.startsWith('U-')).length + 1;
  const newRule = {
    rule_id: `U-${String(seq).padStart(3, '0')}`,
    statement: body.statement,
    scope: body.scope,
    scope_detail: body.scope_detail || null,
    category: body.category,
    citations: [],
    rationale: body.rationale || null,
    origin: 'user_added',
    review: {
      status: 'accepted',
      reviewer: body.reviewer,
      reviewed_at: new Date().toISOString(),
      reason: 'user-added',
      edited_value: null,
    },
  };
  ext.rules.push(newRule);
  ext.updated_at = new Date().toISOString();
  return structuredClone(newRule);
}
