import asyncio
from app.schemas.state.models import ToolErrorType

class ToolException(Exception):
    def __init__(self, message: str, error_type: ToolErrorType, retryable: bool = False):
        super().__init__(message)
        self.tool_error_type = error_type
        self.retryable = retryable

async def web_search_stub(query: str = "", **kwargs) -> dict:
    """Mock web search tool. Fails on empty_query."""
    if not query or query == "empty_query":
        raise ToolException("Query cannot be empty", ToolErrorType.EMPTY_RESULT, retryable=True)
    if query == "malformed":
        raise ToolException("Invalid search syntax", ToolErrorType.MALFORMED_INPUT, retryable=False)
        
    # Simulate work
    await asyncio.sleep(0.1)
    
    return {
        "results": [
            {"title": "Result 1 for " + query, "snippet": "Relevant information..."},
            {"title": "Result 2 for " + query, "snippet": "More details here..."}
        ]
    }

async def reflection_tool(critique_target: str = "", **kwargs) -> dict:
    """Mock reflection/critique tool."""
    await asyncio.sleep(0.05)
    return {
        "feedback": f"Reflection completed. Consider expanding on {critique_target}.",
        "confidence_score": 0.85
    }

async def python_sandbox(code: str = "", **kwargs) -> dict:
    """Mock sandbox. Simulates timeout if code has while True."""
    if "while True" in code:
        await asyncio.sleep(10.0) # Will trigger execution timeout
        
    if "import os" in code:
        raise ToolException("Security violation", ToolErrorType.MALFORMED_INPUT, retryable=False)
        
    await asyncio.sleep(0.1)
    return {
        "stdout": "Hello World\n",
        "stderr": "",
        "exit_code": 0
    }

async def sql_query_tool(query: str = "", **kwargs) -> dict:
    """Mock SQL tool."""
    if "DROP" in query.upper():
        raise ToolException("Destructive operation blocked", ToolErrorType.INVALID_SQL, retryable=False)
        
    if "SELECT" not in query.upper():
        raise ToolException("Not a valid select query", ToolErrorType.INVALID_SQL, retryable=True)
        
    await asyncio.sleep(0.1)
    return {
        "rows": [{"id": 1, "value": "test"}],
        "row_count": 1
    }
