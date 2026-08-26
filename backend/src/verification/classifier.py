"""Deterministic evidence classifier.

Assigns a semantic :class:`EvidenceType` to a piece of evidence using a
transparent, ordered set of rules over three signals, in decreasing order of
trust:

1. **Source type** — the strongest signal. A ``PAYMENT_RECORD`` is payment
   proof, an ``ACCESS_LOG`` is access proof, and so on. When the ingest layer
   already knows the provenance of a file, we honour it.
2. **Extracted fact types** — when the source is a generic container
   (``CSV_LOG``/``JSON_LOG``/``PDF_DOCUMENT``/``OTHER``) we infer meaning from
   the *facts* present: a 3-D Secure cryptogram implies an authentication log,
   a payment id plus amount implies a payment record, and so on.
3. **Content keywords** — a last-resort lexical fallback.

The classifier is intentionally deterministic and side-effect free: the same
inputs always produce the same output, and every decision carries a
human-readable rationale so it can be surfaced in the audit trail. It never
guesses with false confidence — when no rule fires it returns
``USAGE_METRICS`` (the neutral bucket) at low confidence, which maps to no
requirement's ``required_evidence_types`` and therefore earns no type-match
credit downstream. Ambiguity costs coverage; it never fabricates it.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from pydantic import BaseModel, Field

from src.domain.enums import EvidenceSourceType, EvidenceType, FactType


class ClassificationResult(BaseModel):
    """The outcome of classifying a single evidence item."""

    semantic_type: EvidenceType = Field(description="The inferred semantic evidence type")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the classification")
    rationale: str = Field(description="Human-readable explanation of why this type was chosen")
    signals: List[str] = Field(default_factory=list, description="The signals that fired, for auditing")


# --- Signal 1: source type is authoritative for these formats -----------------
_SOURCE_TYPE_MAP: dict[EvidenceSourceType, EvidenceType] = {
    EvidenceSourceType.PAYMENT_RECORD: EvidenceType.PAYMENT_PROOF,
    EvidenceSourceType.INVOICE: EvidenceType.PAYMENT_PROOF,
    EvidenceSourceType.ACCESS_LOG: EvidenceType.ACCESS_PROOF,
    EvidenceSourceType.SERVER_LOG: EvidenceType.ACCESS_PROOF,
    EvidenceSourceType.DOWNLOAD_LOG: EvidenceType.DELIVERY_PROOF,
    EvidenceSourceType.AUTHENTICATION_LOG: EvidenceType.AUTHENTICATION_PROOF,
    EvidenceSourceType.DEVICE_LOG: EvidenceType.IDENTITY_PROOF,
    EvidenceSourceType.SUPPORT_CHAT: EvidenceType.COMMUNICATION,
    EvidenceSourceType.EMAIL: EvidenceType.COMMUNICATION,
    EvidenceSourceType.TERMS_OF_SERVICE: EvidenceType.POLICY_DOCUMENT,
    EvidenceSourceType.HISTORICAL_TRANSACTION: EvidenceType.HISTORICAL_MATCH,
}

# Generic containers whose meaning must be inferred from facts / content.
_GENERIC_SOURCES = {
    EvidenceSourceType.CSV_LOG,
    EvidenceSourceType.JSON_LOG,
    EvidenceSourceType.PDF_DOCUMENT,
    EvidenceSourceType.SCREENSHOT,
    EvidenceSourceType.OTHER,
}


def _classify_by_facts(fact_types: set[FactType]) -> Optional[tuple[EvidenceType, str]]:
    """Infer a type from the set of extracted fact types (ordered by specificity)."""
    # 3-D Secure authentication artefacts are unambiguous.
    if fact_types & {FactType.ECI_VALUE, FactType.CAVV, FactType.DS_TRANS_ID}:
        return EvidenceType.AUTHENTICATION_PROOF, "3-D Secure cryptogram facts present (ECI/CAVV/DS_TRANS_ID)"
    # A session id is a login/auth signal.
    if FactType.SESSION_ID in fact_types:
        return EvidenceType.AUTHENTICATION_PROOF, "session identifier present (login/MFA event)"
    # Payment id + amount is a settlement record.
    if FactType.PAYMENT_ID in fact_types and FactType.AMOUNT in fact_types:
        return EvidenceType.PAYMENT_PROOF, "payment id and amount present"
    # Device fingerprint / device id → identity linkage.
    if fact_types & {FactType.DEVICE_FINGERPRINT, FactType.DEVICE_ID}:
        return EvidenceType.IDENTITY_PROOF, "device identifier/fingerprint present"
    # Access pattern: a timestamped, IP-bearing, account-scoped event.
    if {FactType.IP_ADDRESS, FactType.TIMESTAMP, FactType.ACCOUNT_ID} <= fact_types:
        return EvidenceType.ACCESS_PROOF, "timestamped IP-scoped account activity present"
    # Communication: a person plus a contact channel.
    if FactType.EMAIL_ADDRESS in fact_types and FactType.CUSTOMER_NAME in fact_types:
        return EvidenceType.COMMUNICATION, "customer name and email present"
    return None


# --- Signal 3: lexical fallback -----------------------------------------------
_KEYWORD_RULES: list[tuple[tuple[str, ...], EvidenceType, str]] = [
    (("terms of service", "i agree", "consent to", "accepted the terms"), EvidenceType.POLICY_DOCUMENT, "terms/consent language"),
    (("tracking number", "delivered", "shipment", "downloaded", "download link"), EvidenceType.DELIVERY_PROOF, "delivery/download language"),
    (("logged in", "login", "signed in", "accessed", "session started"), EvidenceType.ACCESS_PROOF, "access/login language"),
    (("otp", "one-time password", "3ds", "authenticated", "cardholder verified"), EvidenceType.AUTHENTICATION_PROOF, "authentication language"),
    (("refund", "chargeback", "did not authorize", "never received", "dispute"), EvidenceType.COMMUNICATION, "dispute/support language"),
]


def _classify_by_content(content: str) -> Optional[tuple[EvidenceType, str]]:
    lowered = content.lower()
    for keywords, etype, why in _KEYWORD_RULES:
        if any(k in lowered for k in keywords):
            return etype, f"content keyword match: {why}"
    return None


def classify_evidence(
    source_type: EvidenceSourceType,
    fact_types: Iterable[FactType],
    raw_content: Optional[str] = None,
) -> ClassificationResult:
    """Classify an evidence item into a semantic :class:`EvidenceType`.

    Args:
        source_type: The ingest-detected source/format of the evidence.
        fact_types: The fact types extracted from the evidence.
        raw_content: Optional raw text, used only for the lexical fallback.

    Returns:
        A :class:`ClassificationResult` with the inferred type, a confidence in
        ``[0, 1]``, and a rationale suitable for the audit trail.
    """
    fact_set = set(fact_types)
    signals: List[str] = []

    # Signal 1: authoritative source type.
    if source_type in _SOURCE_TYPE_MAP:
        etype = _SOURCE_TYPE_MAP[source_type]
        signals.append(f"source_type={source_type.value}")
        # A confirming fact-level signal raises confidence.
        fact_hint = _classify_by_facts(fact_set)
        confidence = 0.95 if (fact_hint and fact_hint[0] == etype) else 0.85
        return ClassificationResult(
            semantic_type=etype,
            confidence=confidence,
            rationale=f"Source type '{source_type.value}' maps directly to {etype.value}.",
            signals=signals,
        )

    # Signal 2: infer from extracted facts (generic containers).
    fact_hint = _classify_by_facts(fact_set)
    if fact_hint is not None:
        etype, why = fact_hint
        signals.append(f"facts:{why}")
        return ClassificationResult(
            semantic_type=etype,
            confidence=0.75,
            rationale=f"Inferred {etype.value} from extracted facts ({why}).",
            signals=signals,
        )

    # Signal 3: lexical fallback.
    if raw_content:
        content_hint = _classify_by_content(raw_content)
        if content_hint is not None:
            etype, why = content_hint
            signals.append(f"content:{why}")
            return ClassificationResult(
                semantic_type=etype,
                confidence=0.5,
                rationale=f"Inferred {etype.value} from {why}.",
                signals=signals,
            )

    # No rule fired: neutral, low-confidence bucket. This earns no type-match
    # credit downstream — ambiguity must not manufacture coverage.
    return ClassificationResult(
        semantic_type=EvidenceType.USAGE_METRICS,
        confidence=0.2,
        rationale="No source/fact/content signal matched; left unclassified (neutral).",
        signals=["default"],
    )
