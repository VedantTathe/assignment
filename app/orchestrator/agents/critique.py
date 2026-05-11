from app.schemas.state import AgentState, CritiqueIssue
from app.schemas.state.models import ToolCall
from app.orchestrator.tracing import with_agent_tracing, safe_trace_event, TraceEventType
from app.orchestrator.tools.registry import get_tool
from app.orchestrator.tools.executor import execute_tool_safe
from langchain_core.runnables import RunnableConfig

@with_agent_tracing("critique")
async def critique_node(state: AgentState, config: RunnableConfig) -> dict:
    """Mock critique agent. Fails deterministically if 'ambiguous' in user_input on first pass."""
    session = config.get("configurable", {}).get("db_session")
    stream_queue = config.get("configurable", {}).get("stream_queue")
    thread_id = state.get("thread_id", "unknown")
    
    user_input = state.get("user_input", "").lower()
    retry_count = state.get("retry_count", 0)
    
    # Tool Orchestration: Reflection
    tool_func = get_tool("reflection")
    tool_input = {"critique_target": user_input}
    
    tool_result = await execute_tool_safe(
        tool_func=tool_func,
        tool_name="reflection",
        input_payload=tool_input,
        session=session,
        thread_id=thread_id,
        stream_queue=stream_queue
    )
    
    tool_call = ToolCall(
        tool_name="reflection",
        input_payload=tool_input,
        result=tool_result,
        accepted_by_agent=True
    )
    
    # Deterministic rule: if ambiguous and no retries yet -> FAIL
    if "ambiguous" in user_input and retry_count == 0:
        issue = CritiqueIssue(
            span="entire response",
            issue_type="hallucination",
            confidence=0.9,
            explanation="The answer is ambiguous and requires refinement.",
            suggested_fix="Be more precise."
        )
        
        if session or stream_queue:
            await safe_trace_event(
                session=session, thread_id=thread_id,
                event_type=TraceEventType.RETRY_TRIGGERED, agent_name="critique",
                metadata={"reason": "Ambiguous input detected"},
                stream_queue=stream_queue
            )
            
        return {
            "routing_history": ["critique_failed"],
            "tool_calls": [tool_call],
            "retry_count": retry_count + 1,
            "token_usage_by_agent": {"critique": 50}
        }
    
    # Else -> PASS
    return {
        "routing_history": ["critique_passed"],
        "tool_calls": [tool_call],
        "token_usage_by_agent": {"critique": 30}
    }

def critique_router(state: AgentState) -> str:
    """Explicit conditional router."""
    history = state.get("routing_history", [])
    
    if not history:
        return "END"
        
    last_status = history[-1]
    
    if last_status == "critique_passed":
        return "END"
        
    retry_count = state.get("retry_count", 0)
    if retry_count >= 3:
        return "END"  # Graceful exit after max retries
        
    # Else, route to synthesis to retry
    return "synthesis"
