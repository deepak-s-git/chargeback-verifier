from src.domain.enums import EvidenceSourceType, ExtractionMethod, FactType
from src.domain.models import ExtractedFact, Provenance
from src.extraction.llm_client import LLMClient
from src.extraction.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE
from src.extraction.schemas import ExtractionOutputSchema

class EvidenceExtractor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def extract(self, evidence_text: str, source_type: EvidenceSourceType) -> ExtractionOutputSchema:
        user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
            evidence_source_type=source_type.value,
            evidence_text=evidence_text
        )
        return await self.llm_client.extract_structured(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_schema=ExtractionOutputSchema
        )

    def to_extracted_facts(self, extraction: ExtractionOutputSchema, evidence_id: str) -> list[ExtractedFact]:
        facts = []
        for entity in extraction.entities:
            try:
                fact_type = FactType(entity.entity_type)
            except ValueError:
                fact_type = FactType.OTHER
                
            provenance = Provenance(
                source_file=evidence_id,
                source_location="extracted via LLM",
                content_hash=Provenance.compute_hash(entity.value)
            )
            
            fact = ExtractedFact(
                type=fact_type,
                value=entity.value,
                confidence=entity.confidence,
                extraction_method=ExtractionMethod.LLM,
                provenance=provenance
            )
            facts.append(fact)
        return facts
