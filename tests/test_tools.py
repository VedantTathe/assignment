import asyncio
import pytest
from app.orchestrator.tools.registry import get_tool
from app.orchestrator.tools.executor import execute_tool_safe
from app.schemas.state.models import ToolErrorType

@pytest.mark.asyncio
async def test_tool_success_contract():
    tool = get_tool("web_search")
    result = await execute_tool_safe(
        tool_func=tool,
        tool_name="web_search",
        input_payload={"query": "valid query"},
        session=None,
        thread_id="test-thread",
        stream_queue=None
    )
    
    assert result.status == "success"
    assert "results" in result.output
    assert result.error_type == ToolErrorType.NONE
    assert result.retryable is False
    assert result.latency_ms >= 0

@pytest.mark.asyncio
async def test_tool_empty_result_contract():
    tool = get_tool("web_search")
    result = await execute_tool_safe(
        tool_func=tool,
        tool_name="web_search",
        input_payload={"query": "empty_query"},
        session=None,
        thread_id="test-thread",
        stream_queue=None
    )
    
    assert result.status == "error"
    assert result.error_type == ToolErrorType.EMPTY_RESULT
    assert result.retryable is True

@pytest.mark.asyncio
async def test_tool_timeout_contract():
    tool = get_tool("python_sandbox")
    result = await execute_tool_safe(
        tool_func=tool,
        tool_name="python_sandbox",
        input_payload={"code": "while True: pass"},
        session=None,
        thread_id="test-thread",
        stream_queue=None,
        timeout_seconds=0.2 # Fast timeout for test
    )
    
    assert result.status == "error"
    assert result.error_type == ToolErrorType.TIMEOUT
    assert result.retryable is True

@pytest.mark.asyncio
async def test_tool_invalid_sql_contract():
    tool = get_tool("sql_query")
    result = await execute_tool_safe(
        tool_func=tool,
        tool_name="sql_query",
        input_payload={"query": "DROP TABLE users;"},
        session=None,
        thread_id="test-thread"
    )
    
    assert result.status == "error"
    assert result.error_type == ToolErrorType.INVALID_SQL
    assert result.retryable is False

async def run_all():
    print("\n--- Running Tool Framework Tests ---")
    await test_tool_success_contract()
    print("SUCCESS: test_tool_success_contract")
    await test_tool_empty_result_contract()
    print("SUCCESS: test_tool_empty_result_contract")
    await test_tool_timeout_contract()
    print("SUCCESS: test_tool_timeout_contract")
    await test_tool_invalid_sql_contract()
    print("SUCCESS: test_tool_invalid_sql_contract")
    print("\n==================================================")
    print("ALL TOOL FRAMEWORK TESTS PASSED!")
    print("==================================================\n")

if __name__ == "__main__":
    asyncio.run(run_all())
