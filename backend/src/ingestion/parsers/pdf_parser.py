import io
from typing import List, Dict, Any
import PyPDF2

def parse_pdf(content: bytes) -> List[Dict[str, Any]]:
    """Extract text from PDF file content.
    
    Args:
        content: Raw PDF file content in bytes
        
    Returns:
        List of dictionaries with extracted text per page
    """
    records = []
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        
        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text:
                records.append({
                    "page_number": i + 1,
                    "text": text.strip()
                })
    except Exception:
        # Graceful handling of extraction failures
        pass
        
    return records
