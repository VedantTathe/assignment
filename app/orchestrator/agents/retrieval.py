from app.schemas.state import AgentState, AgentArtifact, Citation
from app.schemas.state.models import ToolCall
from app.orchestrator.tracing import with_agent_tracing, TraceEventType
from app.orchestrator.tools.registry import get_tool
from app.orchestrator.tools.executor import execute_tool_safe
from langchain_core.runnables import RunnableConfig

@with_agent_tracing("retrieval")
async def retrieval_node(state: AgentState, config: RunnableConfig) -> dict:
    """Mock retrieval agent. Uses safe_trace_event directly for TOOL_CALLED."""
    session = config.get("configurable", {}).get("db_session")
    stream_queue = config.get("configurable", {}).get("stream_queue")
    thread_id = state.get("thread_id", "unknown")
    
    # Tool Orchestration: Web Search
    tool_func = get_tool("web_search")
    tool_input = {"query": state.get("user_input", "")}
    
    tool_result = await execute_tool_safe(
        tool_func=tool_func,
        tool_name="web_search",
        input_payload=tool_input,
        session=session,
        thread_id=thread_id,
        stream_queue=stream_queue
    )
    
    tool_call = ToolCall(
        tool_name="web_search",
        input_payload=tool_input,
        result=tool_result,
        accepted_by_agent=True
    )
    
    citation = Citation(
        chunk_id="doc_1",
        source_url="http://mock.internal",
        supporting_text="Mocked vector db response",
        referenced_sentences=[]
    )
    
    artifact = AgentArtifact(
        agent_name="retrieval",
        output_text="Retrieved contextual documents.",
        citations=[citation],
        critique_issues=[],
        token_usage=100
    )
    
    return {
        "routing_history": ["retrieval"],
        "tool_calls": [tool_call],
        "agent_artifacts": {"retrieval": artifact},
        "token_usage_by_agent": {"retrieval": 100}
    }
