from typing import Any
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel

def safe_serialize_trace_data(obj: Any) -> Any:
    """Recursively serializes datetimes, enums, Pydantic models for JSON/DB insertion."""
    if isinstance(obj, BaseModel):
        return safe_serialize_trace_data(obj.model_dump())
    elif isinstance(obj, dict):
        return {k: safe_serialize_trace_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_serialize_trace_data(i) for i in obj]
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value
    return obj
