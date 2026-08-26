from pydantic import BaseModel

class ValidationResult(BaseModel):
    valid: bool
    issues: list[str]

def validate_file(file_content: bytes, mime_type: str, max_size_mb: int = 10) -> ValidationResult:
    issues = []
    
    max_bytes = max_size_mb * 1024 * 1024
    if len(file_content) > max_bytes:
        issues.append(f"File size {len(file_content)} exceeds maximum of {max_bytes} bytes")
        
    if not file_content:
        issues.append("File is empty")
        
    # Basic magic byte checking could be added here
    if mime_type == 'application/pdf' and not file_content.startswith(b'%PDF'):
        issues.append("Invalid PDF magic bytes")
        
    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues
    )
