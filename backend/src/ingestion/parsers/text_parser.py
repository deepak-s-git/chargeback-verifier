import re
from typing import List, Dict, Any

def parse_text(content: bytes) -> List[Dict[str, Any]]:
    """Parse plain text content into logical segments.
    
    Splits content by common boundaries like blank lines or timestamps.
    
    Args:
        content: Raw text file content in bytes
        
    Returns:
        List of dictionaries with segment text and optional extracted info
    """
    text_content = content.decode("utf-8", errors="replace")
    
    # Try splitting by double newlines (paragraphs/blank lines)
    segments = re.split(r'\n\s*\n', text_content)
    
    # Filter out empty segments
    segments = [s.strip() for s in segments if s.strip()]
    
    # If no segments found via double newline, we can just treat each line as a segment,
    # or return the whole text as one segment if it's short.
    if len(segments) <= 1:
        # Split by newlines if it's multiline
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        if len(lines) > 5:
            segments = lines
        else:
            segments = [text_content] if text_content.strip() else []
            
    records = []
    for seg in segments:
        records.append({
            "text": seg,
            "length": len(seg)
        })
        
    return records
