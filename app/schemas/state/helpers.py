from typing import Dict, Any, Union
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

def safe_json_serialize(obj: Any) -> Any:
    """
    Normalizes datetime, enum, and nested Pydantic structures into JSON-safe representations
    compatible with LangGraph checkpoint persistence.
    """
    if isinstance(obj, BaseModel):
        return safe_json_serialize(obj.model_dump())
    elif isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_serialize(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value
    return obj

def calculate_total_tokens(usage_dict: Dict[str, int]) -> int:
    """Helper to sum up token usage safely."""
    return sum(usage_dict.values()) if usage_dict else 0
