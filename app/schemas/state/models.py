from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict

from enum import Enum

class ToolErrorType(str, Enum):
    TIMEOUT = "TIMEOUT"
    MALFORMED_INPUT = "MALFORMED_INPUT"
    EMPTY_RESULT = "EMPTY_RESULT"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    INVALID_SQL = "INVALID_SQL"
    NONE = "NONE"

class ToolResult(BaseModel):
    status: str = Field("pending", description="Status of the tool call (e.g. pending, success, error)")
    output: Dict[str, Any] = Field(default_factory=dict, description="Results from the tool")
    latency_ms: int = Field(0, description="Execution time in milliseconds")
    retryable: bool = Field(False, description="Whether this error should trigger an orchestration retry")
    error_type: ToolErrorType = Field(ToolErrorType.NONE, description="Structured error type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or trace info")

    class Config:
        frozen = True

class ToolCall(BaseModel):
    tool_name: str = Field(..., description="Name of the tool executed")
    input_payload: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the tool")
    result: Optional[ToolResult] = Field(None, description="The execution result of the tool")
    accepted_by_agent: bool = Field(False, description="Whether the agent accepted the tool output")
    retry_attempt: int = Field(0, description="Number of times this tool call was retried")
    
    class Config:
        frozen = True

class Citation(BaseModel):
    chunk_id: str = Field(..., description="Unique identifier for the retrieved chunk")
    source_url: str = Field(..., description="URL or source reference")
    supporting_text: str = Field(..., description="The actual text used for citation")
    referenced_sentences: List[str] = Field(default_factory=list, description="Sentences in the generated response that use this citation")

class CritiqueIssue(BaseModel):
    span: str = Field(..., description="The text span containing the issue")
    issue_type: str = Field(..., description="Type of issue (e.g., hallucination, ungrounded, tone)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the critique")
    explanation: str = Field(..., description="Detailed explanation of the issue")
    suggested_fix: str = Field(..., description="Suggested correction for the text")

class AgentArtifact(BaseModel):
    agent_name: str = Field(..., description="Name of the agent that produced this artifact")
    output_text: str = Field(..., description="The generated response or synthesis")
    citations: List[Citation] = Field(default_factory=list, description="Citations used in this artifact")
    critique_issues: List[CritiqueIssue] = Field(default_factory=list, description="Issues identified by the critique node")
    token_usage: int = Field(0, description="Tokens consumed to generate this artifact")

class PolicyViolation(BaseModel):
    violation_type: str = Field(..., description="Type of violation (e.g., inappropriate_content, formatting)")
    description: str = Field(..., description="Details about the policy violation")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the violation occurred")
