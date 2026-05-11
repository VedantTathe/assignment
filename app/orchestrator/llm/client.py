import asyncio
import time
from typing import List, Dict, Any, Optional
from app.orchestrator.llm.providers.base import AsyncLLMProvider
from app.orchestrator.llm.streaming import stream_token
from app.orchestrator.tracing import safe_trace_event, TraceEventType
from app.schemas.state.models import ToolResult, ToolErrorType

async def generate_completion(
    provider: AsyncLLMProvider,
    messages: List[Dict[str, str]],
    thread_id: str,
    session: Any = None,
    stream_queue: Optional[asyncio.Queue] = None,
    timeout_seconds: float = 30.0,
    **kwargs
) -> ToolResult:
    """
    Wraps the LLM provider stream with timeout boundaries, structured error
    catching, and lightweight SSE fanout. Returns a structured ToolResult.
    """
    start_time = time.time()
    
    await safe_trace_event(
        session=session, thread_id=thread_id,
        event_type=TraceEventType.TOOL_CALLED, agent_name="llm_generation",
        stream_queue=stream_queue
    )
    
    async def _consume_stream():
        full_text = ""
        async for delta in provider.generate_stream(messages, **kwargs):
            full_text += delta
            await stream_token(delta, thread_id, stream_queue)
        return full_text

    try:
        final_text = await asyncio.wait_for(_consume_stream(), timeout=timeout_seconds)
        latency_ms = int((time.time() - start_time) * 1000)
        
        result = ToolResult(
            status="success",
            output={"text": final_text},
            latency_ms=latency_ms,
            retryable=False,
            error_type=ToolErrorType.NONE
        )
        
        await safe_trace_event(
            session=session, thread_id=thread_id,
            event_type=TraceEventType.TOOL_COMPLETED, agent_name="llm_generation",
            latency_ms=latency_ms,
            stream_queue=stream_queue
        )
        return result
        
    except asyncio.TimeoutError:
        latency_ms = int((time.time() - start_time) * 1000)
        result = ToolResult(
            status="error",
            output={},
            latency_ms=latency_ms,
            retryable=True,
            error_type=ToolErrorType.TIMEOUT,
            metadata={"timeout_seconds": timeout_seconds}
        )
        await safe_trace_event(
            session=session, thread_id=thread_id,
            event_type=TraceEventType.TOOL_FAILED, agent_name="llm_generation",
            latency_ms=latency_ms,
            metadata={"error": "LLM Generation Timeout"},
            stream_queue=stream_queue
        )
        return result
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        result = ToolResult(
            status="error",
            output={},
            latency_ms=latency_ms,
            retryable=True,
            error_type=ToolErrorType.EXECUTION_ERROR,
            metadata={"error": str(e)}
        )
        await safe_trace_event(
            session=session, thread_id=thread_id,
            event_type=TraceEventType.TOOL_FAILED, agent_name="llm_generation",
            latency_ms=latency_ms,
            metadata={"error": str(e)},
            stream_queue=stream_queue
        )
        return result
