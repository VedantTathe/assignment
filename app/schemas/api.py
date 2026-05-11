from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

class TraceResponse(BaseModel):
    thread_id: str
    status: str
    current_agent: Optional[str]
    token_usage: int
    latency_ms: int
    tool_calls_in_progress: int
