"""LLM-backed fact extraction.

Extraction is the *only* place a language model touches the pipeline, and even
here its output is treated as a set of *proposals* that must survive
deterministic grounding downstream — the model can suggest a fact, but if that
fact's value does not appear in the source content, claim verification will
refuse to rely on it.

Two correctness fixes over the previous version:

1. The user prompt is assembled without ``str.format`` on the evidence body.
   Evidence routinely contains ``{`` / ``}`` (every JSON log does), which made
   ``.format`` raise ``KeyError``/``ValueError`` and take down ingestion. We
   only substitute into the fixed template, never interpret the evidence.
2. Facts proposed by the LLM are stamped with the SHA-256 of the *evidence
   item's raw content* (not the hash of the value in isolation), so their
   provenance is consistent with regex-extracted facts and the grounding check
   in :mod:`claim_verifier` is meaningful.
"""

from typing import List

from src.domain.enums import EvidenceSourceType, ExtractionMethod, FactType
from src.domain.models import ExtractedFact, Provenance
from src.extraction.llm_client import LLMClient
from src.extraction.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE
from src.extraction.schemas import ExtractionOutputSchema


class EvidenceExtractor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    @staticmethod
    def _build_user_prompt(evidence_text: str, source_type: EvidenceSourceType) -> str:
        # Substitute only into the fixed template; never .format the evidence
        # body (it may contain braces) and delimit it as untrusted data.
        return (
            EXTRACTION_USER_PROMPT_TEMPLATE
            .replace("{evidence_source_type}", source_type.value)
            .replace("{evidence_text}", evidence_text)
        )

    async def extract(self, evidence_text: str, source_type: EvidenceSourceType) -> ExtractionOutputSchema:
        user_prompt = self._build_user_prompt(evidence_text, source_type)
        return await self.llm_client.extract_structured(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_schema=ExtractionOutputSchema,
        )

    def to_extracted_facts(
        self, extraction: ExtractionOutputSchema, evidence_id: str, raw_content: str
    ) -> List[ExtractedFact]:
        """Convert LLM-proposed entities into provenance-bearing facts.

        The provenance hash is computed over ``raw_content`` (the source the
        model read), so downstream grounding compares like with like.
        """
        content_hash = Provenance.compute_hash(raw_content)
        facts: List[ExtractedFact] = []
        for entity in extraction.entities:
            try:
                fact_type = FactType(entity.entity_type)
            except ValueError:
                fact_type = FactType.OTHER

            facts.append(
                ExtractedFact(
                    type=fact_type,
                    value=entity.value,
                    confidence=entity.confidence,
                    extraction_method=ExtractionMethod.LLM,
                    provenance=Provenance(
                        source_file=evidence_id,
                        source_location="LLM extraction",
                        content_hash=content_hash,
                    ),
                )
            )
        return facts
