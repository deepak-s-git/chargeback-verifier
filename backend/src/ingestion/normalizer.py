import ipaddress
from datetime import datetime, timezone
from typing import Optional
import dateparser

def normalize_timestamp(raw: str) -> Optional[datetime]:
    """Normalize a raw timestamp string to UTC datetime.
    
    Args:
        raw: The raw timestamp string
        
    Returns:
        UTC datetime object or None if invalid
    """
    if not raw or not isinstance(raw, str):
        return None
        
    # Attempt parsing with dateparser
    dt = dateparser.parse(raw, settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True})
    if dt:
        return dt.astimezone(timezone.utc)
    return None

def normalize_ip(raw: str) -> Optional[str]:
    """Validate and normalize IPv4/IPv6 addresses.
    
    Args:
        raw: The raw IP address string
        
    Returns:
        Normalized IP string or None if invalid
    """
    if not raw or not isinstance(raw, str):
        return None
        
    try:
        # ipaddress module handles validation and basic normalization
        ip = ipaddress.ip_address(raw.strip())
        return str(ip)
    except ValueError:
        return None

def normalize_amount(raw: str, currency: str = 'INR') -> Optional[int]:
    """Convert an amount string to the smallest unit (e.g., paise for INR, cents for USD).
    
    Args:
        raw: The raw amount string
        currency: The currency code (default: INR)
        
    Returns:
        Integer amount in smallest unit or None if invalid
    """
    if not raw:
        return None
        
    # Remove currency symbols and commas
    clean_val = str(raw).replace(',', '').replace('₹', '').replace('$', '').replace('€', '').replace('£', '').strip()
    
    try:
        val = float(clean_val)
        # Most major currencies use 2 decimal places, so multiply by 100
        # For simplicity, assuming 2 decimal places for all common ones
        return int(val * 100)
    except ValueError:
        return None
