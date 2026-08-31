/**
 * Typed client for the DisputeShield API.
 *
 * The dev server proxies `/api` to the FastAPI backend (see `vite.config.ts`),
 * and the backend mounts every router under `/api`, so the base URL is `/api`
 * with no rewriting. Each function returns the parsed, typed body; transport
 * and HTTP errors are normalised to {@link ApiError} so callers can render a
 * message without unwrapping axios internals.
 */

import axios, { AxiosError } from 'axios';
import type {
  AuditLogEntry,
  CaseAnalysis,
  CaseCreateRequest,
  DemoLoadResponse,
  DisputeCase,
  EvidenceItem,
  EvidencePackage,
  TimelineEvent,
} from './types';

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

/** A transport/HTTP error reduced to a human-readable message + status. */
export class ApiError extends Error {
  status: number | null;
  constructor(message: string, status: number | null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function toApiError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const ax = err as AxiosError<{ detail?: string }>;
    const status = ax.response?.status ?? null;
    const detail = ax.response?.data?.detail;
    if (detail) return new ApiError(detail, status);
    if (ax.code === 'ECONNABORTED') return new ApiError('The request timed out.', status);
    if (ax.request && !ax.response) {
      return new ApiError('Cannot reach the DisputeShield API. Is the backend running?', null);
    }
    return new ApiError(ax.message || 'Request failed.', status);
  }
  return new ApiError(err instanceof Error ? err.message : 'Unexpected error.', null);
}

async function unwrap<T>(p: Promise<{ data: T }>): Promise<T> {
  try {
    return (await p).data;
  } catch (err) {
    throw toApiError(err);
  }
}

/* ---- Cases -------------------------------------------------------------- */

/** List all cases (summary form; `evidence_items` is populated only by {@link getCase}). */
export const listCases = (): Promise<DisputeCase[]> => unwrap(client.get('/cases/'));

/** Fetch one case, including its `evidence_items`. */
export const getCase = (caseId: string): Promise<DisputeCase> =>
  unwrap(client.get(`/cases/${encodeURIComponent(caseId)}`));

/** Create a new case. Returns the full case model. */
export const createCase = (body: CaseCreateRequest): Promise<DisputeCase> =>
  unwrap(client.post('/cases/', body));

/**
 * Run the deterministic analysis for a case and return the full explainable
 * result (score, requirements, claims, contradictions, timeline, CE 3.0,
 * injection finding, gate decision).
 */
export const analyzeCase = (caseId: string): Promise<CaseAnalysis> =>
  unwrap(client.post(`/cases/${encodeURIComponent(caseId)}/analyze`));

/** Idempotent read of the same analysis payload as {@link analyzeCase}. */
export const getAnalysis = (caseId: string): Promise<CaseAnalysis> =>
  unwrap(client.get(`/cases/${encodeURIComponent(caseId)}/analysis`));

/** Persisted timeline (may be empty before analysis has run and stored it). */
export const getTimeline = (caseId: string): Promise<TimelineEvent[]> =>
  unwrap(client.get(`/cases/${encodeURIComponent(caseId)}/timeline`));

/** Build (and return) the compiled, review-gated evidence package. */
export const getPackage = (caseId: string): Promise<EvidencePackage> =>
  unwrap(client.get(`/cases/${encodeURIComponent(caseId)}/package`));

/** The AI/decision audit trail for a case. */
export const getAuditTrail = (caseId: string): Promise<AuditLogEntry[]> =>
  unwrap(client.get(`/cases/${encodeURIComponent(caseId)}/audit`));

/** Upload one evidence file (multipart). Returns the created evidence items. */
export const uploadEvidence = async (
  caseId: string,
  file: File,
): Promise<EvidenceItem[]> => {
  const form = new FormData();
  form.append('file', file);
  const res = await unwrap<{ items: EvidenceItem[] }>(
    client.post(`/cases/${encodeURIComponent(caseId)}/evidence`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  );
  return res.items;
};

/* ---- Demo --------------------------------------------------------------- */

/** Load the five canonical demo cases (A–E). */
export const loadDemo = (): Promise<DemoLoadResponse> => unwrap(client.post('/demo/load'));
