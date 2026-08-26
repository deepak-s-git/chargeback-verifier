import pytest
from src.extraction.schemas import ExtractedEventSchema, ExtractedEntitySchema, ExtractionOutputSchema
from src.extraction.prompts import EXTRACTION_USER_PROMPT_TEMPLATE
from src.extraction.llm_client import MockLLMClient
from src.extraction.extractor import EvidenceExtractor
from src.domain.enums import EvidenceSourceType

@pytest.mark.asyncio
async def test_extraction_schema_validation():
    data = {
        "evidence_type": "ACCESS_PROOF",
        "events": [],
        "entities": [{"entity_type": "IP_ADDRESS", "value": "127.0.0.1", "confidence": 0.9}],
        "confidence": 0.95,
        "extraction_notes": "None"
    }
    schema = ExtractionOutputSchema(**data)
    assert schema.confidence == 0.95

@pytest.mark.asyncio
async def test_evidence_extractor():
    client = MockLLMClient()
    extractor = EvidenceExtractor(client)
    result = await extractor.extract("some text", EvidenceSourceType.ACCESS_LOG)
    assert result.confidence == 1.0
