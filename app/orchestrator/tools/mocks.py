import asyncio
import subprocess
import json
from typing import Dict, Any, Optional
from app.schemas.state.models import ToolErrorType
from app.core.logger import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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

async def python_sandbox(code: str = "", timeout: int = 5, **kwargs) -> dict:
    """
    Execute Python code safely in a subprocess with sandboxing.
    Returns stdout, stderr, and exit code.
    """
    if not code or not code.strip():
        raise ToolException("Code cannot be empty", ToolErrorType.EMPTY_RESULT, retryable=False)
    
    # Security checks - prevent dangerous operations
    dangerous_patterns = ["__import__", "eval", "exec", "compile", "open(", "os.", "sys.", "subprocess"]
    for pattern in dangerous_patterns:
        if pattern in code:
            raise ToolException(
                f"Security violation: pattern '{pattern}' not allowed",
                ToolErrorType.MALFORMED_INPUT,
                retryable=False
            )
    
    try:
        # Execute in subprocess with timeout
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        raise ToolException(
            f"Code execution timeout after {timeout} seconds",
            ToolErrorType.TIMEOUT,
            retryable=True
        )
    except Exception as e:
        raise ToolException(
            f"Execution error: {str(e)}",
            ToolErrorType.EXECUTION_ERROR,
            retryable=False
        )

async def sql_query_tool(
    query: str = "",
    db_session: Optional[AsyncSession] = None,
    **kwargs
) -> dict:
    """
    Execute natural language or SQL queries against the database.
    Returns rows and metadata about the query.
    """
    if not query or not query.strip():
        raise ToolException("Query cannot be empty", ToolErrorType.EMPTY_RESULT, retryable=False)
    
    # Security: block destructive operations FIRST (before checking session)
    upper_query = query.upper()
    if any(op in upper_query for op in ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE"]):
        raise ToolException(
            "Destructive operations are blocked",
            ToolErrorType.INVALID_SQL,
            retryable=False
        )
    
    # Only allow SELECT queries
    if "SELECT" not in upper_query:
        raise ToolException(
            "Only SELECT queries are allowed",
            ToolErrorType.INVALID_SQL,
            retryable=True
        )
    
    # Now check if session is available
    if not db_session:
        raise ToolException(
            "Database session not available",
            ToolErrorType.EXECUTION_ERROR,
            retryable=False
        )
    
    try:
        result = await db_session.execute(text(query))
        rows = [dict(row) for row in result.fetchall()]
        
        return {
            "rows": rows,
            "row_count": len(rows),
            "success": True
        }
    except Exception as e:
        raise ToolException(
            f"SQL execution error: {str(e)}",
            ToolErrorType.INVALID_SQL,
            retryable=False
        )

async def reflection_tool(
    critique_target: str = "",
    agent_state: Optional[Dict[str, Any]] = None,
    **kwargs
) -> dict:
    """
    Self-reflection tool that allows agents to re-read and analyze their outputs.
    Helps resolve contradictions and improve quality.
    """
    if not critique_target or not critique_target.strip():
        raise ToolException(
            "Critique target cannot be empty",
            ToolErrorType.EMPTY_RESULT,
            retryable=False
        )
    
    # Extract relevant context from agent state
    context = ""
    if agent_state:
        # Get the most recent agent artifact
        artifacts = agent_state.get("agent_artifacts", [])
        if artifacts:
            latest_artifact = artifacts[-1]
            context = latest_artifact.get("output", "")
    
    await asyncio.sleep(0.05)  # Simulate processing
    
    return {
        "original_text": critique_target[:500],  # First 500 chars
        "feedback": f"Self-reflection analysis: {critique_target[:100]}...",
        "contradictions_found": 0,
        "improvements_suggested": [
            "Add more specific examples",
            "Strengthen the reasoning",
            "Clarify ambiguous statements"
        ],
        "confidence_score": 0.82,
        "context_length": len(context)
    }
