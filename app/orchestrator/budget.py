from app.schemas.state import AgentState
from app.orchestrator.tracing import safe_trace_event, TraceEventType
from app.schemas.state.helpers import calculate_total_tokens
from langchain_core.runnables import RunnableConfig

async def check_budget(state: AgentState, config: RunnableConfig, **kwargs) -> str:
    """
    Deterministic budget manager conditional edge.
    Computes total token usage and triggers compression if limit exceeded.
    """
    session = config.get("configurable", {}).get("db_session")
    stream_queue = config.get("configurable", {}).get("stream_queue")
    thread_id = state.get("thread_id", "unknown")
    
    total_tokens = calculate_total_tokens(state.get("token_usage_by_agent", {}))
    limit = config.get("configurable", {}).get("token_limit", 4000)
    
    if total_tokens > limit:
        if session or stream_queue:
            await safe_trace_event(
                session=session,
                thread_id=thread_id,
                event_type=TraceEventType.POLICY_VIOLATION,
                agent_name="budget_manager",
                metadata={"violation_type": "budget_exceeded", "description": f"Tokens {total_tokens} > {limit}"},
                stream_queue=stream_queue
            )
        return "compression"
    return "synthesis"
