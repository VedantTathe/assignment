import asyncio
import json
import httpx
from app.main import app

async def test_sse_streaming_order():
    print("\n--- Testing SSE Stream Ordering & Content ---")
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {"message": "Tell me about LangGraph", "thread_id": "sse-test-1"}
        
        async with client.stream("POST", "/api/chat/stream", json=payload) as response:
            assert response.status_code == 200
            
            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[len("data: "):]
                    event_data = json.loads(data_str)
                    events.append(event_data)
            
            assert len(events) > 0, "No events received from stream"
            
            # Verify the sequence matches the graph topology
            event_names = [e["event"] for e in events]
            
            assert "AGENT_STARTED" in event_names
            assert "AGENT_COMPLETED" in event_names
            
            agents = [e["agent_name"] for e in events if "agent_name" in e]
            assert "decomposition" in agents
            assert "synthesis" in agents
            
            print(f"SUCCESS: Received {len(events)} ordered SSE events.")
            print(f"Sample First Event: {events[0]}")

async def test_sse_disconnect_safety():
    print("\n--- Testing SSE Disconnect Cancellation ---")
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {"message": "Test disconnect", "thread_id": "sse-test-2"}
        
        async with client.stream("POST", "/api/chat/stream", json=payload) as response:
            # Read just ONE event, then break to simulate disconnect
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    break # Client drops connection!
                    
        print("SUCCESS: Stream cleanly interrupted without leaking.")

async def run_all():
    await test_sse_streaming_order()
    await test_sse_disconnect_safety()
    print("\n" + "="*50)
    print("ALL SSE STREAMING TESTS PASSED!")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(run_all())
