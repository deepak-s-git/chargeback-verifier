import json
from typing import List

from src.domain.enums import EvidenceSourceType, EvidenceType, ExtractionMethod, FactType
from src.domain.models import EvidenceItem, ExtractedFact, Provenance
from src.ingestion.entity_extractor import extract_all
from src.ingestion.parsers.csv_parser import parse_csv
from src.ingestion.parsers.json_parser import parse_json
from src.ingestion.parsers.pdf_parser import parse_pdf
from src.ingestion.parsers.text_parser import parse_text

def ingest_evidence_file(file_path: str, file_content: bytes, mime_type: str, case_id: str) -> List[EvidenceItem]:
    """Ingest a file, parse it, extract entities, and return EvidenceItems.
    
    Args:
        file_path: The original file path
        file_content: Raw bytes of the file
        mime_type: MIME type of the file
        case_id: ID of the dispute case
        
    Returns:
        List of created EvidenceItem objects
    """
    records = []
    
    # 1 & 2: Detect file type and route to appropriate parser
    if mime_type == 'text/csv' or file_path.endswith('.csv'):
        records = parse_csv(file_content)
        source_type = EvidenceSourceType.CSV_LOG
    elif mime_type == 'application/json' or file_path.endswith('.json'):
        records = parse_json(file_content)
        source_type = EvidenceSourceType.JSON_LOG
    elif mime_type == 'application/pdf' or file_path.endswith('.pdf'):
        records = parse_pdf(file_content)
        source_type = EvidenceSourceType.PDF_DOCUMENT
    else:
        records = parse_text(file_content)
        source_type = EvidenceSourceType.OTHER
        
    evidence_items = []
    
    # 3 & 4: Run entity extraction and create EvidenceItems
    for i, record in enumerate(records):
        # Convert record back to string for regex extraction
        text_content = json.dumps(record) if isinstance(record, dict) else str(record)
        
        extracted_entities = extract_all(text_content)
        
        extracted_facts = []
        
        # Calculate content hash
        content_hash = Provenance.compute_hash(text_content)
        
        for fact_type, values in extracted_entities.items():
            for value in values:
                provenance = Provenance(
                    source_file=file_path,
                    source_location=f"Record {i}",
                    content_hash=content_hash
                )
                
                fact = ExtractedFact(
                    type=fact_type,
                    value=value,
                    confidence=1.0,
                    extraction_method=ExtractionMethod.REGEX,
                    provenance=provenance
                )
                extracted_facts.append(fact)
        
        evidence_item = EvidenceItem(
            case_id=case_id,
            source_type=source_type,
            semantic_type=EvidenceType.USAGE_METRICS,  # Needs classification later
            file_path=file_path,
            raw_content=text_content,
            extracted_facts=extracted_facts,
            confidence=1.0
        )
        
        evidence_items.append(evidence_item)
        
    return evidence_items
