import asyncio
import time
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.state.models import ToolResult, ToolErrorType
from app.orchestrator.tracing import safe_trace_event, TraceEventType
from app.core.logger import logger

async def execute_tool_safe(
    tool_func: callable,
    tool_name: str,
    input_payload: Dict[str, Any],
    session: Optional[AsyncSession],
    thread_id: str,
    stream_queue: Optional[asyncio.Queue] = None,
    timeout_seconds: float = 5.0
) -> ToolResult:
    """
    Executes a deterministic or non-deterministic tool with comprehensive
    timeouts, tracing, error boundary catching, and structured outputs.
    """
    # Trace Tool Start
    await safe_trace_event(
        session=session, thread_id=thread_id,
        event_type=TraceEventType.TOOL_CALLED, agent_name=tool_name,
        metadata={"tool_name": tool_name, "input_payload": input_payload},
        stream_queue=stream_queue
    )

    start_time = time.time()
    try:
        # Enforce execution timeout
        result_dict = await asyncio.wait_for(tool_func(**input_payload), timeout=timeout_seconds)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        result = ToolResult(
            status="success",
            output=result_dict,
            latency_ms=latency_ms,
            retryable=False,
            error_type=ToolErrorType.NONE
        )

        # Trace Tool Success
        await safe_trace_event(
            session=session, thread_id=thread_id,
            event_type=TraceEventType.TOOL_COMPLETED, agent_name=tool_name,
            latency_ms=latency_ms,
            metadata={"tool_name": tool_name, "input_payload": input_payload, "result": result.model_dump()},
            stream_queue=stream_queue
        )
        return result
        
    except asyncio.TimeoutError:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.warning(f"Tool {tool_name} timed out after {latency_ms}ms")
        
        result = ToolResult(
            status="error",
            output={},
            latency_ms=latency_ms,
            retryable=True, # Timeouts are generally retryable
            error_type=ToolErrorType.TIMEOUT,
            metadata={"timeout_seconds": timeout_seconds}
        )
        
        await safe_trace_event(
            session=session, thread_id=thread_id,
            event_type=TraceEventType.TOOL_FAILED, agent_name=tool_name,
            latency_ms=latency_ms,
            metadata={"tool_name": tool_name, "input_payload": input_payload, "result": result.model_dump()},
            stream_queue=stream_queue
        )
        return result
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.exception(f"Tool {tool_name} crashed.", error=str(e))
        
        # If it's a known error contract that the mock tool raises, we could map it.
        # But generally unhandled exceptions are EXECUTION_ERROR.
        error_type = getattr(e, "tool_error_type", ToolErrorType.EXECUTION_ERROR)
        retryable = getattr(e, "retryable", False)
        
        result = ToolResult(
            status="error",
            output={},
            latency_ms=latency_ms,
            retryable=retryable,
            error_type=error_type,
            metadata={"error": str(e)}
        )
        
        await safe_trace_event(
            session=session, thread_id=thread_id,
            event_type=TraceEventType.TOOL_FAILED, agent_name=tool_name,
            latency_ms=latency_ms,
            metadata={"tool_name": tool_name, "input_payload": input_payload, "result": result.model_dump()},
            stream_queue=stream_queue
        )
        return result
