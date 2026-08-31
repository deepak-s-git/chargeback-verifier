/**
 * DisputeShield API contract.
 *
 * These types mirror the backend Pydantic models (`backend/src/domain/models.py`
 * and `enums.py`) and the analysis serializer in `backend/src/api/routes/cases.py`
 * *exactly* — field names, optionality and enum string values are the wire
 * contract. Do not "improve" a name here without changing the backend; a drift
 * is a bug, not a convenience. Every enum is a string union (the backend uses
 * `str, Enum`, so values arrive as their string form).
 */

/* ---- Enums (string unions matching the backend) ------------------------- */

export type CardNetwork = 'VISA' | 'MASTERCARD';

export type DisputeCategory = 'FRAUD_UNAUTHORIZED';

export type DisputePhase =
  | 'FRAUD'
  | 'RETRIEVAL'
  | 'CHARGEBACK'
  | 'PRE_ARBITRATION'
  | 'ARBITRATION';

export type CaseStatus =
  | 'OPEN'
  | 'INGESTING'
  | 'ANALYZING'
  | 'REVIEW_REQUIRED'
  | 'PACKAGE_READY'
  | 'SUBMITTED'
  | 'WON'
  | 'LOST'
  | 'CLOSED';

export type EvidenceSourceType =
  | 'ACCESS_LOG'
  | 'SERVER_LOG'
  | 'EMAIL'
  | 'INVOICE'
  | 'SCREENSHOT'
  | 'CSV_LOG'
  | 'JSON_LOG'
  | 'PDF_DOCUMENT'
  | 'SUPPORT_CHAT'
  | 'PAYMENT_RECORD'
  | 'TERMS_OF_SERVICE'
  | 'AUTHENTICATION_LOG'
  | 'DEVICE_LOG'
  | 'DOWNLOAD_LOG'
  | 'HISTORICAL_TRANSACTION'
  | 'OTHER';

export type EvidenceType =
  | 'PAYMENT_PROOF'
  | 'IDENTITY_PROOF'
  | 'ACCESS_PROOF'
  | 'DELIVERY_PROOF'
  | 'AUTHENTICATION_PROOF'
  | 'COMMUNICATION'
  | 'POLICY_DOCUMENT'
  | 'USAGE_METRICS'
  | 'HISTORICAL_MATCH';

export type FactType =
  | 'IP_ADDRESS'
  | 'DEVICE_ID'
  | 'DEVICE_FINGERPRINT'
  | 'EMAIL_ADDRESS'
  | 'TIMESTAMP'
  | 'CUSTOMER_NAME'
  | 'ACCOUNT_ID'
  | 'PAYMENT_ID'
  | 'ORDER_ID'
  | 'AMOUNT'
  | 'CURRENCY'
  | 'USER_AGENT'
  | 'GEO_LOCATION'
  | 'SESSION_ID'
  | 'DOWNLOAD_HASH'
  | 'LICENSE_KEY'
  | 'ECI_VALUE'
  | 'CAVV'
  | 'DS_TRANS_ID'
  | 'AVS_RESULT'
  | 'CVV_RESULT'
  | 'ACTION_DESCRIPTION'
  | 'PRODUCT_NAME'
  | 'REFUND_AMOUNT'
  | 'OTHER';

export type RequirementStatus =
  | 'SATISFIED'
  | 'PARTIALLY_SATISFIED'
  | 'MISSING'
  | 'CONTRADICTED'
  | 'NOT_APPLICABLE';

/** Rule weight of a requirement (from the card-network rule definition). */
export type RequirementStrength = 'REQUIRED' | 'STRONG' | 'SUPPORTING';

export type ClaimStatus = 'VERIFIED' | 'BLOCKED' | 'NEEDS_REVIEW' | 'DRAFT';

export type Recommendation = 'CONTEST' | 'REVIEW' | 'INSUFFICIENT' | 'ABSTAIN';

export type TimelineAnomalyType =
  | 'IMPOSSIBLE_ORDER'
  | 'SUSPICIOUS_GAP'
  | 'DUPLICATE_EVENT'
  | 'FUTURE_TIMESTAMP'
  | 'MISSING_EXPECTED_EVENT';

export type ExtractionMethod = 'DETERMINISTIC' | 'REGEX' | 'LLM' | 'OCR';

export type ScoringFactorType = 'POSITIVE' | 'NEGATIVE' | 'MISSING';

export type ContradictionType =
  | 'IP_MISMATCH'
  | 'IDENTITY_MISMATCH'
  | 'AMOUNT_MISMATCH'
  | 'TIMELINE_ORDER'
  | 'USAGE_BEFORE_PURCHASE'
  | 'CUSTOMER_STATEMENT_CONFLICT'
  | 'FUTURE_TIMESTAMP';

/** Human-review gate decision (`backend/src/orchestrator/gate.py`). */
export type GateStatus =
  | 'MANDATORY_REVIEW'
  | 'READY'
  | 'NEEDS_REVIEW'
  | 'NOT_RECOMMENDED';

/** Severity string used across anomalies and contradictions. */
export type Severity = 'LOW' | 'MEDIUM' | 'HIGH';

/* ---- Core domain models ------------------------------------------------- */

export interface Provenance {
  source_file: string;
  source_location: string;
  content_hash: string;
}

export interface ExtractedFact {
  type: FactType;
  value: string;
  confidence: number;
  extraction_method: ExtractionMethod;
  provenance: Provenance;
}

export interface EvidenceItem {
  id: string;
  case_id: string;
  source_type: EvidenceSourceType;
  semantic_type: EvidenceType;
  file_path: string | null;
  raw_content: string | null;
  extracted_facts: ExtractedFact[];
  confidence: number;
  created_at: string;
}

export interface TimelineAnomaly {
  type: TimelineAnomalyType;
  description: string;
  severity: string;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  description: string;
  evidence_id: string;
  event_type: string | null;
  actor: string | null;
  ip_address: string | null;
  anomalies: TimelineAnomaly[];
}

export interface Claim {
  id: string;
  description: string;
  status: ClaimStatus;
  supporting_evidence_ids: string[];
  block_reason: string | null;
}

export interface Requirement {
  id: string;
  name: string;
  description: string;
  status: RequirementStatus;
  strength: string;
  coverage: number;
  is_auto_win: boolean;
  evidence_candidates: string[];
  satisfied_fact_types: string[];
  missing_fact_types: string[];
  source_reference: string;
}

export interface Contradiction {
  claim_a_id: string | null;
  claim_b_id: string | null;
  evidence_a_id: string | null;
  evidence_b_id: string | null;
  description: string;
  severity: string;
  type: string;
}

export interface ScoringFactor {
  name: string;
  type: ScoringFactorType;
  points: number;
  description: string;
  evidence_ids: string[];
}

export interface EvidenceScore {
  total_score: number;
  factors: ScoringFactor[];
  recommendation: Recommendation;
}

export interface EvidencePackage {
  case_id: string;
  claims: Claim[];
  requirements: Requirement[];
  score: EvidenceScore | null;
  timeline: TimelineEvent[];
  contradictions: Contradiction[];
  recommendation: Recommendation | null;
  review_required: boolean;
  review_reasons: string[];
  network_submission: Record<string, unknown> | null;
  generated_at: string;
}

export interface DisputeCase {
  id: string;
  merchant_id: string;
  transaction_id: string;
  dispute_id: string | null;
  amount: number;
  currency: string;
  network: CardNetwork;
  category: DisputeCategory;
  reason_code: string;
  phase: DisputePhase;
  status: CaseStatus;
  transaction_date: string | null;
  respond_by: string | null;
  created_at: string;
  updated_at: string;
  evidence_items: EvidenceItem[];
  claims: Claim[];
  package: EvidencePackage | null;
}

export interface AuditLogEntry {
  id: string;
  case_id: string;
  timestamp: string;
  pipeline_stage: string;
  model_used: string;
  prompt_hash: string | null;
  decision: string;
  confidence: number;
  latency_ms: number;
}

/** A single qualifying prior transaction under Visa CE 3.0. */
export interface QualifyingTransaction {
  evidence_id: string;
  days_before_dispute: number;
  matching_elements: string[];
}

export interface CE30Result {
  qualified: boolean;
  matching_elements: string[];
  qualifying_transactions: string[];
  qualifying_details: QualifyingTransaction[];
  reason: string;
}

/**
 * The analysis payload returned by `POST/GET /cases/{id}/analyze|analysis`
 * (`_analysis_payload` in cases.py). Note `score` is the full nested
 * {@link EvidenceScore} — read `score.total_score`, never `score.score`.
 */
export interface CaseAnalysis {
  case_id: string;
  status: CaseStatus;
  score: EvidenceScore;
  recommendation: Recommendation;
  gate_status: GateStatus;
  gate_reasons: string[];
  requirements: Requirement[];
  claims: Claim[];
  contradictions: Contradiction[];
  timeline: TimelineEvent[];
  ce30: CE30Result | null;
  injection_detected: boolean;
  injection_patterns: string[];
}

/* ---- Request payloads --------------------------------------------------- */

export interface CaseCreateRequest {
  merchant_id: string;
  transaction_id: string;
  amount: number;
  currency: string;
  network: CardNetwork;
  reason_code: string;
  dispute_id?: string | null;
  transaction_date?: string | null;
  respond_by?: string | null;
}

export interface DemoLoadResponse {
  status: string;
  created_cases: string[];
  count: number;
}

export interface EvidenceUploadResponse {
  items: EvidenceItem[];
}
