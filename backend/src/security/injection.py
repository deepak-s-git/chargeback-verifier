import re
from pydantic import BaseModel

class InjectionResult(BaseModel):
    detected: bool
    patterns_matched: list[str]
    sanitized_text: str

INJECTION_PATTERNS = [
    re.compile(r'ignore previous instructions', re.IGNORECASE),
    re.compile(r'you are now', re.IGNORECASE),
    re.compile(r'system:', re.IGNORECASE),
    re.compile(r'<system>', re.IGNORECASE),
    re.compile(r'forget everything', re.IGNORECASE),
    re.compile(r'override instructions', re.IGNORECASE),
    re.compile(r'new instructions', re.IGNORECASE),
    re.compile(r'act as', re.IGNORECASE),
    re.compile(r'pretend to be', re.IGNORECASE)
]

def detect_injection(text: str) -> InjectionResult:
    matched = []
    sanitized = text
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            matched.append(pattern.pattern)
            sanitized = pattern.sub('', sanitized)
    return InjectionResult(
        detected=len(matched) > 0,
        patterns_matched=matched,
        sanitized_text=sanitized
    )

def sanitize_evidence_text(text: str) -> str:
    return detect_injection(text).sanitized_text
