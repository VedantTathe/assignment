from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import uuid
from typing import Dict, Any
from app.schemas.state import AgentState
from app.orchestrator.graph import graph
from app.db.session import async_session

router = APIRouter()

@router.post("/chat/stream")
async def chat_stream(request: Request, body: Dict[str, Any]):
    """
    Streams LangGraph orchestration events via SSE using exactly the same
    deterministic tracing schema used for database persistence.
    """
    user_input = body.get("message", "")
    thread_id = body.get("thread_id", str(uuid.uuid4()))
    
    stream_queue = asyncio.Queue()
    
    async def graph_runner():
        try:
            async with async_session() as session:
                initial_state = {
                    "thread_id": thread_id,
                    "user_input": user_input,
                    "retry_count": 0
                }
                config = {
                    "configurable": {
                        "db_session": session,
                        "stream_queue": stream_queue,
                        "token_limit": 4000
                    }
                }
                await graph.ainvoke(initial_state, config)
        except Exception as e:
            await stream_queue.put({
                "event": "graph_error",
                "thread_id": thread_id,
                "agent_name": "system",
                "metadata": {"error": str(e)},
                "timestamp": ""
            })
        finally:
            await stream_queue.put(None)
            
    task = asyncio.create_task(graph_runner())
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    task.cancel()
                    break
                event = await stream_queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            task.cancel()
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
