import csv
import io
from typing import List, Dict, Any

def parse_csv(content: bytes) -> List[Dict[str, Any]]:
    """Parse CSV content into a list of dictionaries.
    
    Handles common CSV issues like different delimiters or quotes.
    
    Args:
        content: Raw CSV file content in bytes
        
    Returns:
        List of dictionaries where keys are headers and values are row data
    """
    text_content = content.decode("utf-8", errors="replace")
    
    # Try to detect dialect
    try:
        dialect = csv.Sniffer().sniff(text_content[:1024])
    except csv.Error:
        # Fallback to standard dialect
        dialect = csv.excel
        
    reader = csv.DictReader(io.StringIO(text_content), dialect=dialect)
    records = []
    
    for row in reader:
        # Filter out completely empty rows
        if any(v.strip() for k, v in row.items() if v):
            records.append({k: v for k, v in row.items() if k})
            
    return records
