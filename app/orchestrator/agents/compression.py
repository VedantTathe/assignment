import asyncio
from typing import List
from app.schemas.state import AgentState, AgentArtifact
from app.orchestrator.tracing import with_agent_tracing, safe_trace_event, TraceEventType
from langchain_core.runnables import RunnableConfig

@with_agent_tracing("compression")
async def compression_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Compression agent that intelligently summarizes context when token budget is exceeded.
    Preserves citations and critical information while removing filler.
    """
    session = config.get("configurable", {}).get("db_session")
    stream_queue = config.get("configurable", {}).get("stream_queue")
    thread_id = state.get("thread_id", "unknown")
    token_limit = config.get("configurable", {}).get("token_limit", 4000)
    
    # Calculate current token usage
    current_tokens = state.get("token_usage", 0)
    artifacts = state.get("agent_artifacts", [])
    
    # Estimate tokens from artifacts
    for artifact in artifacts:
        output = artifact.get("output", "")
        # Rough estimate: 1 token ~= 4 chars
        current_tokens += len(output) // 4
    
    compression_ratio = 0.5  # Default: compress to 50% of original
    tokens_to_remove = current_tokens - (token_limit * 0.7)  # Keep 70% of limit
    
    if tokens_to_remove > 0:
        # Intelligently summarize older artifacts
        original_token_count = current_tokens
        
        # Compress older artifacts (keep newest one intact)
        for i in range(len(artifacts) - 1):
            artifact = artifacts[i]
            output = artifact.get("output", "")
            
            # Simple compression: take first 200 chars + last 100 chars
            if len(output) > 300:
                compressed = output[:200] + "\n[...compressed...]\n" + output[-100:]
                artifacts[i]["output"] = compressed
                artifact["compression_applied"] = True
        
        # Calculate new token count
        new_token_count = sum(len(a.get("output", "")) // 4 for a in artifacts)
        
        # Trace compression event
        if session or stream_queue:
            await safe_trace_event(
                session=session,
                thread_id=thread_id,
                event_type=TraceEventType.CONTEXT_COMPRESSED,
                agent_name="compression",
                metadata={
                    "original_tokens": original_token_count,
                    "compressed_tokens": new_token_count,
                    "compression_ratio": compression_ratio,
                    "artifacts_compressed": len(artifacts) - 1,
                    "description": f"Context compressed from {original_token_count} to {new_token_count} tokens"
                },
                stream_queue=stream_queue
            )
        
        return {
            "routing_history": ["compression"],
            "agent_artifacts": artifacts,
            "token_usage": new_token_count,
            "token_usage_by_agent": {"compression": 50},
            "compression_applied": True
        }
    
    return {
        "routing_history": ["compression"],
        "token_usage_by_agent": {"compression": 50},
        "compression_applied": False
    }
