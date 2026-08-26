import pytest
from datetime import datetime, timezone
from src.ingestion.parsers.csv_parser import parse_csv
from src.ingestion.parsers.json_parser import parse_json
from src.ingestion.parsers.text_parser import parse_text
from src.ingestion.normalizer import normalize_timestamp, normalize_ip, normalize_amount
from src.ingestion.entity_extractor import extract_all
from src.domain.enums import FactType
from src.ingestion.pipeline import ingest_evidence_file

def test_csv_parser():
    content = b"header1,header2\nval1,val2\nval3,val4"
    res = parse_csv(content)
    assert len(res) == 2
    assert res[0]['header1'] == 'val1'

def test_json_parser():
    content = b'{"nested": {"key": "value"}}'
    res = parse_json(content)
    assert len(res) == 1
    assert res[0]['nested_key'] == 'value'

def test_text_parser():
    content = b"Email body\n\nAnother paragraph"
    res = parse_text(content)
    assert len(res) == 2
    assert res[0]['text'] == 'Email body'

def test_normalizers():
    # Timestamp
    dt = normalize_timestamp("2023-10-12T15:30:00Z")
    assert dt is not None
    assert dt.year == 2023
    
    # IP
    ip = normalize_ip(" 192.168.1.1 ")
    assert ip == "192.168.1.1"
    
    # Amount
    amt = normalize_amount("$10.50")
    assert amt == 1050

def test_entity_extractor():
    text = "User IP: 192.168.1.1, email: test@example.com, payment: pay_abc123"
    entities = extract_all(text)
    assert "192.168.1.1" in entities[FactType.IP_ADDRESS]
    assert "test@example.com" in entities[FactType.EMAIL_ADDRESS]
    assert "pay_abc123" in entities[FactType.PAYMENT_ID]

def test_pipeline():
    content = b'{"ip": "192.168.1.1", "email": "test@example.com"}'
    items = ingest_evidence_file("test.json", content, "application/json", "CASE-123")
    assert len(items) == 1
    facts = items[0].extracted_facts
    fact_types = [f.type for f in facts]
    assert FactType.IP_ADDRESS in fact_types
    assert FactType.EMAIL_ADDRESS in fact_types
