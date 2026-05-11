import uuid
import time
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.logger import logger
from app.db.models import ExecutionTrace, ToolExecutionTrace, PolicyViolationTrace
from app.orchestrator.tracing.events import TraceEventType
from app.orchestrator.tracing.serialization import safe_serialize_trace_data

import asyncio
from datetime import datetime

async def trace_event(
    session: AsyncSession,
    thread_id: str,
    event_type: TraceEventType,
    agent_name: str = "orchestrator",
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    state_snapshot: Optional[Dict[str, Any]] = None,
    token_count: int = 0,
    latency_ms: int = 0,
    stream_queue: Optional[asyncio.Queue] = None
) -> str:
    """Async helper to trace execution events to DB and Structlog."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    serialized_meta = safe_serialize_trace_data(metadata) if metadata else None
    serialized_state = safe_serialize_trace_data(state_snapshot) if state_snapshot else None
    
    # 1. Structlog JSON Output
    logger.info(
        f"Trace Event: {event_type.value}",
        thread_id=thread_id,
        correlation_id=correlation_id,
        agent_name=agent_name,
        event_type=event_type.value,
        token_count=token_count,
        latency_ms=latency_ms,
        metadata=serialized_meta
    )
    
    # 2. SSE Fan-out (Compact delta, omit state_snapshot)
    if stream_queue:
        sse_payload = {
            "event": event_type.value,
            "thread_id": thread_id,
            "correlation_id": correlation_id,
            "agent_name": agent_name,
            "token_count": token_count,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": serialized_meta
        }
        try:
            stream_queue.put_nowait(sse_payload)
        except asyncio.QueueFull:
            logger.warning("SSE queue is full, dropping event", correlation_id=correlation_id)
            
    # 3. Database Persistence
    if session:
        new_trace = ExecutionTrace(
            thread_id=thread_id,
            correlation_id=correlation_id,
            agent_name=agent_name,
            event_type=event_type.value,
            token_count=token_count,
            latency_ms=latency_ms,
            state_snapshot=serialized_state,
            metadata_json=serialized_meta
        )
        session.add(new_trace)
        
        # Optional dedicated tables for highly queryable fields
        if event_type in [TraceEventType.TOOL_CALLED, TraceEventType.TOOL_COMPLETED, TraceEventType.TOOL_FAILED] and metadata:
            result_meta = metadata.get("result") or {}
            tool_trace = ToolExecutionTrace(
                correlation_id=correlation_id,
                thread_id=thread_id,
                tool_name=metadata.get("tool_name", "unknown"),
                input_payload=metadata.get("input_payload"),
                output_payload=result_meta.get("output"),
                status=result_meta.get("status", "unknown"),
                latency_ms=result_meta.get("latency_ms", latency_ms)
            )
            session.add(tool_trace)
        
        if event_type == TraceEventType.POLICY_VIOLATION and metadata:
            policy_trace = PolicyViolationTrace(
                correlation_id=correlation_id,
                thread_id=thread_id,
                violation_type=metadata.get("violation_type", "unknown"),
                description=metadata.get("description", ""),
                span=metadata.get("span", "")
            )
            session.add(policy_trace)

        await session.commit()
    return correlation_id

async def reconstruct_timeline(session: AsyncSession, thread_id: str) -> List[Dict[str, Any]]:
    """Retrieves ordered execution timeline for a thread."""
    stmt = select(ExecutionTrace).where(ExecutionTrace.thread_id == thread_id).order_by(ExecutionTrace.timestamp)
    result = await session.execute(stmt)
    traces = result.scalars().all()
    
    timeline = []
    for t in traces:
        timeline.append({
            "correlation_id": t.correlation_id,
            "timestamp": t.timestamp.isoformat() if t.timestamp else None,
            "agent_name": t.agent_name,
            "event_type": t.event_type,
            "token_count": t.token_count,
            "latency_ms": t.latency_ms,
            "metadata": t.metadata_json,
            "state_snapshot": t.state_snapshot
        })
    return timeline

async def safe_trace_event(*args, **kwargs):
    """Wraps trace_event to ensure tracing failures never crash the graph execution."""
    try:
        await trace_event(*args, **kwargs)
    except Exception as e:
        logger.exception("Tracing failed, but orchestration continues.", error=str(e))

from functools import wraps

from langchain_core.runnables import RunnableConfig

def with_agent_tracing(agent_name: str):
    """Decorator to wrap LangGraph nodes with AGENT_STARTED, AGENT_COMPLETED, and exception safety."""
    def decorator(func):
        @wraps(func)
        async def wrapper(state: dict, config: RunnableConfig, **kwargs):
            session = config.get("configurable", {}).get("db_session")
            stream_queue = config.get("configurable", {}).get("stream_queue")
            thread_id = state.get("thread_id", "unknown")
            
            start_time = time.time()
            if session or stream_queue:
                await safe_trace_event(
                    session=session, thread_id=thread_id,
                    event_type=TraceEventType.AGENT_STARTED, agent_name=agent_name,
                    stream_queue=stream_queue
                )
            
            try:
                # Node Execution
                # Safely pass config if the original function expects it
                import inspect
                sig = inspect.signature(func)
                if "config" in sig.parameters:
                    result = await func(state, config=config)
                else:
                    result = await func(state)
                
                latency_ms = int((time.time() - start_time) * 1000)
                if session or stream_queue:
                    await safe_trace_event(
                        session=session, thread_id=thread_id,
                        event_type=TraceEventType.AGENT_COMPLETED, agent_name=agent_name,
                        latency_ms=latency_ms, state_snapshot=result,
                        stream_queue=stream_queue
                    )
                return result
            
            except Exception as e:
                logger.exception(f"Agent {agent_name} crashed.", error=str(e))
                if session or stream_queue:
                    await safe_trace_event(
                        session=session, thread_id=thread_id,
                        event_type=TraceEventType.POLICY_VIOLATION, agent_name=agent_name,
                        metadata={"violation_type": "node_crash", "description": str(e)},
                        stream_queue=stream_queue
                    )
                # Return partial state indicating failure gracefully
                return {
                    "routing_history": [f"{agent_name}_crashed"],
                    "retry_count": state.get("retry_count", 0) + 1
                }
        return wrapper
    return decorator
