import hashlib
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from src.domain.enums import (
    CardNetwork,
    CaseStatus,
    ClaimStatus,
    DisputeCategory,
    DisputePhase,
    EvidenceSourceType,
    EvidenceType,
    ExtractionMethod,
    FactType,
    Recommendation,
    RequirementStatus,
    ScoringFactorType,
    TimelineAnomalyType,
)


def generate_case_id() -> str:
    """Generate a unique case ID."""
    return f"CASE-{str(uuid4())[:8]}"


def generate_evidence_id() -> str:
    """Generate a unique evidence ID."""
    return f"EV-{str(uuid4())[:8]}"


def generate_claim_id() -> str:
    """Generate a unique claim ID."""
    return f"CLM-{str(uuid4())[:8]}"


class Provenance(BaseModel):
    """Traces an extracted fact back to its source."""
    source_file: str = Field(description="Name or path of the source file")
    source_location: str = Field(description="Line number, page number, or context where the fact was found")
    content_hash: str = Field(description="SHA-256 hash of the extracted content")

    @classmethod
    def compute_hash(cls, content: str) -> str:
        """Compute the SHA-256 hash of a string."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


class ExtractedFact(BaseModel):
    """A single piece of information extracted from evidence."""
    type: FactType = Field(description="The semantic type of the fact")
    value: str = Field(description="The extracted value")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    extraction_method: ExtractionMethod = Field(description="How the fact was extracted")
    provenance: Provenance = Field(description="Where the fact came from")


class EvidenceItem(BaseModel):
    """A piece of evidence submitted for a case."""
    id: str = Field(default_factory=generate_evidence_id, description="Unique evidence ID")
    case_id: str = Field(description="ID of the case this evidence belongs to")
    source_type: EvidenceSourceType = Field(description="The format/source of the evidence")
    semantic_type: EvidenceType = Field(description="The semantic meaning of the evidence")
    file_path: Optional[str] = Field(default=None, description="Path to the evidence file")
    raw_content: Optional[str] = Field(default=None, description="Raw text content if available")
    extracted_facts: List[ExtractedFact] = Field(default_factory=list, description="Facts extracted from this evidence")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall confidence in this evidence item")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When this item was created")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate the evidence ID format."""
        if not v.startswith("EV-"):
            raise ValueError("Evidence ID must start with EV-")
        return v


class TimelineAnomaly(BaseModel):
    """An anomaly detected in the event timeline."""
    type: TimelineAnomalyType = Field(description="The type of anomaly")
    description: str = Field(description="Human-readable description of the anomaly")
    severity: str = Field(description="Severity: LOW, MEDIUM, HIGH")


class TimelineEvent(BaseModel):
    """An event in the dispute timeline."""
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event ID")
    timestamp: datetime = Field(description="When the event occurred")
    description: str = Field(description="What happened")
    evidence_id: str = Field(description="ID of the evidence that proves this event")
    anomalies: List[TimelineAnomaly] = Field(default_factory=list, description="Anomalies associated with this event")


class Claim(BaseModel):
    """An assertion made in defense of the dispute."""
    id: str = Field(default_factory=generate_claim_id, description="Unique claim ID")
    description: str = Field(description="The assertion being made")
    status: ClaimStatus = Field(default=ClaimStatus.DRAFT, description="Current status of the claim")
    supporting_evidence_ids: List[str] = Field(default_factory=list, description="IDs of evidence supporting this claim")
    block_reason: Optional[str] = Field(default=None, description="Reason if the claim is blocked")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate the claim ID format."""
        if not v.startswith("CLM-"):
            raise ValueError("Claim ID must start with CLM-")
        return v


class Requirement(BaseModel):
    """A rule from the card network that needs to be satisfied."""
    id: str = Field(description="Requirement ID (from RequirementDefinition)")
    name: str = Field(description="Name of the requirement")
    description: str = Field(description="Description of what is required")
    status: RequirementStatus = Field(default=RequirementStatus.MISSING, description="Whether the requirement is met")
    evidence_candidates: List[str] = Field(default_factory=list, description="IDs of evidence that might satisfy this")
    source_reference: str = Field(description="Citation to the card network rules")


class Contradiction(BaseModel):
    """A contradiction between claims or evidence."""
    claim_a_id: Optional[str] = Field(default=None, description="First conflicting claim")
    claim_b_id: Optional[str] = Field(default=None, description="Second conflicting claim")
    evidence_a_id: Optional[str] = Field(default=None, description="First conflicting evidence")
    evidence_b_id: Optional[str] = Field(default=None, description="Second conflicting evidence")
    description: str = Field(description="Description of the contradiction")
    severity: str = Field(description="Severity: LOW, MEDIUM, HIGH")
    type: str = Field(description="Type of contradiction")


class ScoringFactor(BaseModel):
    """A factor that contributes to the overall evidence score."""
    name: str = Field(description="Name of the factor")
    type: ScoringFactorType = Field(description="Positive, negative, or missing")
    points: float = Field(description="Points awarded or deducted")
    description: str = Field(description="Why these points were given")
    evidence_ids: List[str] = Field(default_factory=list, description="Associated evidence IDs")


class EvidenceScore(BaseModel):
    """The overall score evaluating the strength of the defense."""
    total_score: float = Field(description="Total score (0-100)")
    factors: List[ScoringFactor] = Field(default_factory=list, description="Factors that make up the score")
    recommendation: Recommendation = Field(description="Recommended action based on score")


class EvidencePackage(BaseModel):
    """The final compiled defense package."""
    case_id: str = Field(description="The case this package is for")
    claims: List[Claim] = Field(default_factory=list, description="Claims made in defense")
    requirements: List[Requirement] = Field(default_factory=list, description="Status of network requirements")
    score: Optional[EvidenceScore] = Field(default=None, description="Score of the package")
    timeline: List[TimelineEvent] = Field(default_factory=list, description="Reconstructed timeline")
    contradictions: List[Contradiction] = Field(default_factory=list, description="Any unresolvable contradictions")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When the package was generated")


class DisputeCase(BaseModel):
    """The central model representing a dispute case."""
    id: str = Field(default_factory=generate_case_id, description="Unique case ID")
    merchant_id: str = Field(description="ID of the merchant")
    transaction_id: str = Field(description="Original transaction ID")
    amount: float = Field(description="Disputed amount")
    currency: str = Field(description="Currency code")
    network: CardNetwork = Field(description="Card network")
    category: DisputeCategory = Field(default=DisputeCategory.FRAUD_UNAUTHORIZED, description="Dispute category")
    reason_code: str = Field(description="Network reason code (e.g., '10.4', '4837')")
    phase: DisputePhase = Field(default=DisputePhase.CHARGEBACK, description="Current phase")
    status: CaseStatus = Field(default=CaseStatus.OPEN, description="Current status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the case was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When the case was last updated")
    evidence_items: List[EvidenceItem] = Field(default_factory=list, description="Evidence gathered")
    claims: List[Claim] = Field(default_factory=list, description="Claims generated")
    package: Optional[EvidencePackage] = Field(default=None, description="Final evidence package")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate the case ID format."""
        if not v.startswith("CASE-"):
            raise ValueError("Case ID must start with CASE-")
        return v


class AuditLogEntry(BaseModel):
    """An entry in the audit log for AI decisions."""
    id: str = Field(default_factory=lambda: str(uuid4()), description="Log entry ID")
    case_id: str = Field(description="Associated case ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the action occurred")
    pipeline_stage: str = Field(description="Stage of the pipeline (e.g., EXTRACTION, SCORING)")
    model_used: str = Field(description="Name/version of the AI model used")
    prompt_hash: Optional[str] = Field(default=None, description="Hash of the prompt sent")
    decision: str = Field(description="The decision or output generated")
    confidence: float = Field(description="Confidence of the decision")
    latency_ms: int = Field(description="Latency of the model call in milliseconds")


# API Models
class CaseCreateRequest(BaseModel):
    """Request model for creating a case."""
    merchant_id: str
    transaction_id: str
    amount: float
    currency: str
    network: CardNetwork
    reason_code: str


class CaseResponse(BaseModel):
    """Response model for a case."""
    id: str
    status: CaseStatus
    network: CardNetwork
    reason_code: str
    created_at: datetime
    evidence_count: int


class EvidenceUploadResponse(BaseModel):
    """Response model for evidence upload."""
    evidence_id: str
    case_id: str
    source_type: EvidenceSourceType
    semantic_type: EvidenceType
    status: str
