from pydantic import BaseModel, Field

class ExtractedEventSchema(BaseModel):
    timestamp: str | None = None  # ISO-8601
    event_type: str  # login, download, purchase, support_contact, etc.
    actor: str  # customer, system, merchant, unknown
    description: str
    ip_address: str | None = None
    device_info: str | None = None
    email: str | None = None
    account_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)

class ExtractedEntitySchema(BaseModel):
    entity_type: str  # from FactType enum values
    value: str
    confidence: float = Field(ge=0.0, le=1.0)

class ExtractionOutputSchema(BaseModel):
    evidence_type: str  # from EvidenceType enum values
    events: list[ExtractedEventSchema]
    entities: list[ExtractedEntitySchema]
    confidence: float = Field(ge=0.0, le=1.0)
    extraction_notes: str  # what was ambiguous
