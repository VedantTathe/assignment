from app.schemas.state import AgentState, AgentArtifact
from app.orchestrator.tracing import with_agent_tracing, safe_trace_event, TraceEventType
from langchain_core.runnables import RunnableConfig
from app.orchestrator.llm.client import generate_completion
from app.orchestrator.llm.providers.openai import OpenAIProvider
from app.orchestrator.prompts.renderer import PromptRenderer
from app.orchestrator.prompts.synthesis.v1 import synthesis_spec_v1

@with_agent_tracing("synthesis")
async def synthesis_node(state: AgentState, config: RunnableConfig) -> dict:
    """Mock synthesis agent. Uses versioned artifact keys based on retry_count."""
    session = config.get("configurable", {}).get("db_session")
    stream_queue = config.get("configurable", {}).get("stream_queue")
    thread_id = state.get("thread_id", "unknown")
    
    retry_count = state.get("retry_count", 0)
    versioned_key = f"synthesis_v{retry_count}"
    
    user_input = state.get("user_input", "")
    
    # Extract context
    retrieval_artifact = state.get("agent_artifacts", {}).get("retrieval")
    retrieved_context = retrieval_artifact.output_text if retrieval_artifact else ""
    
    critique_feedback = ""
    if retry_count > 0:
        critique_feedback = "Please address previous critique feedback."
        
    messages = PromptRenderer.render(
        spec=synthesis_spec_v1,
        context={
            "user_input": user_input,
            "retrieved_context": retrieved_context,
            "critique_feedback": critique_feedback
        }
    )
    
    # Inject provider via config, otherwise default to OpenAI
    provider = config.get("configurable", {}).get("llm_provider")
    if not provider:
        provider = OpenAIProvider()
    
    result = await generate_completion(
        provider=provider,
        messages=messages,
        thread_id=thread_id,
        session=session,
        stream_queue=stream_queue,
        timeout_seconds=30.0
    )
    
    # Check for generation failure
    if result.status == "error":
        return {
            "routing_history": ["synthesis_failed"],
            "retry_count": retry_count + 1
        }
        
    output_text = result.output.get("text", "")
    
    artifact = AgentArtifact(
        agent_name="synthesis",
        output_text=output_text,
        citations=[],
        critique_issues=[],
        token_usage=100
    )
    
    if session or stream_queue:
        await safe_trace_event(
            session=session, thread_id=thread_id,
            event_type=TraceEventType.SYNTHESIS_COMPLETED, agent_name="synthesis",
            stream_queue=stream_queue
        )
        
    return {
        "routing_history": ["synthesis"],
        "agent_artifacts": {versioned_key: artifact},
        "token_usage_by_agent": {"synthesis": 100},
        "final_response": output_text
    }
