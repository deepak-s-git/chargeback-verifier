/**
 * Semantic intent mapping.
 *
 * Every risk-bearing enum in the domain (recommendation, gate status,
 * requirement/claim status, severity, scoring-factor sign) is reduced to one of
 * five visual *intents* so the UI expresses "good / caution / neutral /
 * critical / informational" consistently. Components pick a `.pill--{intent}` or
 * `.badge--{intent}` class from the returned value rather than hard-coding
 * colours, which keeps the meaning of a colour identical across every panel.
 */

import type {
  CaseStatus,
  ClaimStatus,
  GateStatus,
  Recommendation,
  RequirementStatus,
  ScoringFactorType,
} from './types';

export type Intent = 'pos' | 'warn' | 'neu' | 'crit' | 'info';

export function recommendationIntent(rec: Recommendation): Intent {
  switch (rec) {
    case 'CONTEST':
      return 'pos';
    case 'REVIEW':
      return 'warn';
    case 'INSUFFICIENT':
      return 'neu';
    case 'ABSTAIN':
      return 'neu';
  }
}

export function gateIntent(status: GateStatus): Intent {
  switch (status) {
    case 'READY':
      return 'pos';
    case 'NEEDS_REVIEW':
      return 'warn';
    case 'MANDATORY_REVIEW':
      return 'crit';
    case 'NOT_RECOMMENDED':
      return 'neu';
  }
}

export function requirementIntent(status: RequirementStatus): Intent {
  switch (status) {
    case 'SATISFIED':
      return 'pos';
    case 'PARTIALLY_SATISFIED':
      return 'warn';
    case 'CONTRADICTED':
      return 'crit';
    case 'MISSING':
      return 'neu';
    case 'NOT_APPLICABLE':
      return 'neu';
  }
}

export function claimIntent(status: ClaimStatus): Intent {
  switch (status) {
    case 'VERIFIED':
      return 'pos';
    case 'NEEDS_REVIEW':
      return 'warn';
    case 'BLOCKED':
      return 'crit';
    case 'DRAFT':
      return 'neu';
  }
}

export function caseStatusIntent(status: CaseStatus): Intent {
  switch (status) {
    case 'WON':
    case 'PACKAGE_READY':
      return 'pos';
    case 'LOST':
      return 'crit';
    case 'REVIEW_REQUIRED':
      return 'warn';
    case 'SUBMITTED':
      return 'info';
    default:
      return 'neu';
  }
}

export function severityIntent(severity: string): Intent {
  switch (severity.toUpperCase()) {
    case 'HIGH':
      return 'crit';
    case 'MEDIUM':
      return 'warn';
    case 'LOW':
      return 'neu';
    default:
      return 'neu';
  }
}

export function scoringFactorIntent(type: ScoringFactorType): Intent {
  switch (type) {
    case 'POSITIVE':
      return 'pos';
    case 'NEGATIVE':
      return 'crit';
    case 'MISSING':
      return 'neu';
  }
}

/** Map a 0–100 score to an intent for the score gauge. */
export function scoreIntent(score: number): Intent {
  if (score >= 75) return 'pos';
  if (score >= 50) return 'warn';
  if (score >= 25) return 'neu';
  return 'crit';
}
