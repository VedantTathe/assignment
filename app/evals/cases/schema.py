from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class EvalFailureType(str, Enum):
    TIMEOUT = "TIMEOUT"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    HALLUCINATION = "HALLUCINATION"
    TOOL_FAILURE = "TOOL_FAILURE"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    PROMPT_INJECTION_SUCCESS = "PROMPT_INJECTION_SUCCESS"
    CONTEXT_OVERFLOW = "CONTEXT_OVERFLOW"
    RATE_LIMIT = "RATE_LIMIT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    ORCHESTRATION_ERROR = "ORCHESTRATION_ERROR"

class EvalSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class EvalCase(BaseModel):
    id: str = Field(..., description="Unique identifier for the evaluation case")
    input_query: str = Field(..., description="The user query to evaluate")
    expected_behavior: str = Field(..., description="Description of the expected graph behavior")
    expected_tools: List[str] = Field(default_factory=list, description="List of tools expected to be invoked")
    adversarial: bool = Field(False, description="Whether this case tests adversarial resilience")
    ambiguity_level: str = Field("low", description="high, medium, low")
    tags: List[str] = Field(default_factory=list, description="Tags for filtering (e.g., prompt_injection, timeout)")
