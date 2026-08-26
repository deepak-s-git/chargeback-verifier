import json
from typing import List, Dict, Any, Union

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """Flatten a nested dictionary.
    
    Args:
        d: The dictionary to flatten
        parent_key: Prefix for nested keys
        sep: Separator between key levels
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def parse_json(content: bytes) -> List[Dict[str, Any]]:
    """Parse JSON content into a list of flat dictionaries.
    
    Handles single objects (returns list of 1) and arrays (returns list of many).
    
    Args:
        content: Raw JSON file content in bytes
        
    Returns:
        List of flattened dictionaries
    """
    text_content = content.decode("utf-8", errors="replace")
    
    try:
        data = json.loads(text_content)
    except json.JSONDecodeError:
        return []
        
    if not isinstance(data, list):
        data = [data]
        
    records = []
    for item in data:
        if isinstance(item, dict):
            records.append(flatten_dict(item))
        else:
            # If it's a primitive type or list, just wrap it in a dict
            records.append({"value": item})
            
    return records
