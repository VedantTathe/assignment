from typing import Optional, Dict, Any
from pydantic import BaseModel

class ToolResult(BaseModel):
    status: str  # "success" | "error"
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    suggested_fix: Optional[str] = None
