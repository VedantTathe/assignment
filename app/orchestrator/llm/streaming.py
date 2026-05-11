import asyncio
from typing import Optional
from app.core.logger import logger

async def stream_token(delta: str, thread_id: str, stream_queue: Optional[asyncio.Queue]):
    """Pushes a lightweight token event non-blockingly."""
    if not stream_queue:
        return
        
    payload = {
        "event": "llm_token",
        "thread_id": thread_id,
        "delta": delta
    }
    
    try:
        stream_queue.put_nowait(payload)
    except asyncio.QueueFull:
        logger.warning("Stream queue full, dropping token.")
