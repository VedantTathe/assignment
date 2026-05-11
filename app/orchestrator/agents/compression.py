from app.schemas.state import AgentState
from app.orchestrator.tracing import with_agent_tracing, safe_trace_event, TraceEventType
from langchain_core.runnables import RunnableConfig

@with_agent_tracing("compression")
async def compression_node(state: AgentState, config: RunnableConfig) -> dict:
    """Mock compression agent. Summarizes filler, preserves structured citations."""
    session = config.get("configurable", {}).get("db_session")
    stream_queue = config.get("configurable", {}).get("stream_queue")
    thread_id = state.get("thread_id", "unknown")
    
    # Simulate preserving structure but shrinking tokens
    if session or stream_queue:
        await safe_trace_event(
            session=session, thread_id=thread_id,
            event_type=TraceEventType.CONTEXT_COMPRESSED, agent_name="compression",
            metadata={"description": "Context shrunk by 50%"},
            stream_queue=stream_queue
        )
        
    return {
        "routing_history": ["compression"],
        "token_usage_by_agent": {"compression": 50}
    }
