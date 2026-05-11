from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any

class SSEEvent(BaseModel):
    event: str
    thread_id: str
    correlation_id: Optional[str] = None
    agent_name: str
    token_count: int = 0
    latency_ms: int = 0
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")
