/**
 * Display formatters shared across stages.
 */

export function formatScope(scope) {
  return (
    {
      global: 'Global',
      safety_only: 'Safety',
      efficacy_only: 'Efficacy',
      domain_specific: 'Domain',
      population_specific: 'Population',
    }[scope] || scope
  );
}

export function formatSectionRole(role) {
  return (
    {
      administrative: 'Administrative',
      objectives_estimands: 'Objectives / Estimands',
      analysis_populations: 'Populations',
      endpoints: 'Endpoints',
      statistical_methods: 'Stat methods',
      safety_analyses: 'Safety',
      efficacy_analyses: 'Efficacy',
      ae_definitions: 'AE definitions',
      missing_data_handling: 'Missing data',
      interim_analyses: 'Interim',
      multiplicity: 'Multiplicity',
      subgroups: 'Subgroups',
      visit_windows: 'Visit windows',
      derived_variables: 'Derivations',
      changes_from_protocol: 'Protocol changes',
      references: 'References',
      other: 'Other',
    }[role] || role
  );
}

export function formatStatus(status) {
  return (
    {
      pending: 'Pending',
      accepted: 'Accepted',
      edited: 'Edited',
      rejected: 'Rejected',
    }[status] || status
  );
}

export function formatExtractionStatus(status) {
  return (
    {
      running: 'Running',
      awaiting_review: 'Awaiting review',
      approved: 'Approved',
      failed: 'Failed',
    }[status] || status
  );
}

export function formatOrigin(origin) {
  return origin === 'implied' ? 'Implied' : 'Explicit';
}

export function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function truncate(text, n = 80) {
  if (!text) return '';
  return text.length <= n ? text : text.slice(0, n - 1) + '…';
}

export function isSafetyClass(scope) {
  return scope === 'safety_only';
}
export function isEfficacyClass(scope) {
  return scope === 'efficacy_only';
}
