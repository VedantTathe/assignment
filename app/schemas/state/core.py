from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from app.schemas.state.models import ToolCall, AgentArtifact, PolicyViolation
from app.schemas.state.reducers import (
    append_messages,
    deep_merge_artifacts,
    append_tool_calls,
    append_routing_history,
    append_violations,
    merge_token_usage
)

class AgentState(TypedDict):
    thread_id: str
    user_input: str
    messages: Annotated[List[Dict[str, Any]], append_messages]
    
    agent_artifacts: Annotated[Dict[str, AgentArtifact], deep_merge_artifacts]
    tool_calls: Annotated[List[ToolCall], append_tool_calls]
    routing_history: Annotated[List[str], append_routing_history]
    policy_violations: Annotated[List[PolicyViolation], append_violations]
    token_usage_by_agent: Annotated[Dict[str, int], merge_token_usage]
    
    retry_count: int
    final_response: Optional[str]
