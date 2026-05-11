import asyncio
import pytest
from typing import AsyncGenerator, Dict, List
from app.orchestrator.llm.providers.base import AsyncLLMProvider
from app.orchestrator.llm.client import generate_completion
from app.schemas.state.models import ToolErrorType

class MockLLMProvider(AsyncLLMProvider):
    def __init__(self, should_timeout: bool = False, should_fail: bool = False):
        self.should_timeout = should_timeout
        self.should_fail = should_fail
        
    async def generate_stream(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> AsyncGenerator[str, None]:
        if self.should_fail:
            raise Exception("Mocked API Failure")
            
        if self.should_timeout:
            await asyncio.sleep(10.0)
            yield "This won't be reached"
            return
            
        chunks = ["This ", "is ", "a ", "mocked ", "synthesis ", "response."]
        for chunk in chunks:
            await asyncio.sleep(0.01)
            yield chunk

@pytest.mark.asyncio
async def test_llm_safe_generation_success():
    provider = MockLLMProvider()
    stream_queue = asyncio.Queue()
    
    result = await generate_completion(
        provider=provider,
        messages=[{"role": "user", "content": "hello"}],
        thread_id="test-llm-1",
        session=None,
        stream_queue=stream_queue
    )
    
    assert result.status == "success"
    assert result.output["text"] == "This is a mocked synthesis response."
    
    # Check SSE Queue for token streams
    events = []
    while not stream_queue.empty():
        events.append(stream_queue.get_nowait())
        
    token_events = [e for e in events if e.get("event") == "llm_token"]
    assert len(token_events) == 6
    assert token_events[0]["delta"] == "This "

@pytest.mark.asyncio
async def test_llm_safe_generation_timeout():
    provider = MockLLMProvider(should_timeout=True)
    
    result = await generate_completion(
        provider=provider,
        messages=[{"role": "user", "content": "hello"}],
        thread_id="test-llm-2",
        session=None,
        timeout_seconds=0.1
    )
    
    assert result.status == "error"
    assert result.error_type == ToolErrorType.TIMEOUT
    assert result.retryable is True

@pytest.mark.asyncio
async def test_llm_safe_generation_api_failure():
    provider = MockLLMProvider(should_fail=True)
    
    result = await generate_completion(
        provider=provider,
        messages=[{"role": "user", "content": "hello"}],
        thread_id="test-llm-3",
        session=None
    )
    
    assert result.status == "error"
    assert result.error_type == ToolErrorType.EXECUTION_ERROR
    assert result.retryable is True

async def run_all():
    print("\n--- Running LLM Integration Tests ---")
    await test_llm_safe_generation_success()
    print("SUCCESS: test_llm_safe_generation_success")
    await test_llm_safe_generation_timeout()
    print("SUCCESS: test_llm_safe_generation_timeout")
    await test_llm_safe_generation_api_failure()
    print("SUCCESS: test_llm_safe_generation_api_failure")
    print("\n==================================================")
    print("ALL LLM INTEGRATION TESTS PASSED!")
    print("==================================================\n")

if __name__ == "__main__":
    asyncio.run(run_all())
