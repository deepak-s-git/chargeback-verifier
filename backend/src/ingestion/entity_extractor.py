import re
from typing import List, Tuple, Dict
from src.domain.enums import FactType

def extract_ip_addresses(text: str) -> List[str]:
    """Extract IPv4 and IPv6 addresses from text."""
    if not text:
        return []
    
    ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ipv6_pattern = r'\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b|\b(?:[A-Fa-f0-9]{1,4}:)*::(?:[A-Fa-f0-9]{1,4}:)*[A-Fa-f0-9]{1,4}\b'
    
    ipv4s = re.findall(ipv4_pattern, text)
    ipv6s = re.findall(ipv6_pattern, text)
    
    # Basic validation for ipv4
    valid_ipv4s = []
    for ip in ipv4s:
        parts = ip.split('.')
        if all(0 <= int(p) <= 255 for p in parts):
            valid_ipv4s.append(ip)
    
    return list(set(valid_ipv4s + ipv6s))

def extract_email_addresses(text: str) -> List[str]:
    """Extract email addresses from text."""
    if not text:
        return []
    pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    return list(set(re.findall(pattern, text)))

def extract_payment_ids(text: str) -> List[str]:
    """Extract payment IDs (e.g., pay_xxx, pi_xxx)."""
    if not text:
        return []
    pattern = r'\b(?:pay|pi)_[a-zA-Z0-9]+\b'
    return list(set(re.findall(pattern, text)))

def extract_order_ids(text: str) -> List[str]:
    """Extract order IDs (e.g., order_xxx, ord_xxx)."""
    if not text:
        return []
    pattern = r'\b(?:order|ord)_[a-zA-Z0-9]+\b'
    return list(set(re.findall(pattern, text)))

def extract_timestamps(text: str) -> List[str]:
    """Extract timestamps (ISO-8601 and common patterns)."""
    if not text:
        return []
    # Simplified regex for ISO 8601 and basic dates
    pattern = r'\b\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?\b'
    return list(set(re.findall(pattern, text)))

def extract_amounts(text: str) -> List[Tuple[str, str]]:
    """Extract amounts with currency (e.g., $10.00, 50 INR)."""
    if not text:
        return []
    results = []
    # Look for $XX.XX or ₹XX.XX
    symbol_pattern = r'([$₹€£])\s*(\d+(?:,\d+)*(?:\.\d+)?)'
    for match in re.finditer(symbol_pattern, text):
        currency_map = {'$': 'USD', '₹': 'INR', '€': 'EUR', '£': 'GBP'}
        results.append((match.group(2), currency_map.get(match.group(1), 'UNKNOWN')))
        
    # Look for XX.XX INR/USD
    text_pattern = r'(\d+(?:,\d+)*(?:\.\d+)?)\s+(INR|USD|EUR|GBP)'
    for match in re.finditer(text_pattern, text):
        results.append((match.group(1), match.group(2)))
        
    return list(set(results))

def extract_device_ids(text: str) -> List[str]:
    """Extract device IDs (UUIDs)."""
    if not text:
        return []
    uuid_pattern = r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'
    return list(set(re.findall(uuid_pattern, text)))

def extract_all(text: str) -> Dict[FactType, List[str]]:
    """Run all extractors and return typed results."""
    return {
        FactType.IP_ADDRESS: extract_ip_addresses(text),
        FactType.EMAIL_ADDRESS: extract_email_addresses(text),
        FactType.PAYMENT_ID: extract_payment_ids(text),
        FactType.ORDER_ID: extract_order_ids(text),
        FactType.TIMESTAMP: extract_timestamps(text),
        FactType.AMOUNT: [amt for amt, _ in extract_amounts(text)],
        FactType.CURRENCY: [cur for _, cur in extract_amounts(text)],
        FactType.DEVICE_ID: extract_device_ids(text),
    }
