from app.orchestrator.tools.mocks import (
    web_search_stub,
    reflection_tool,
    python_sandbox,
    sql_query_tool
)

# Centralized lightweight registry
TOOLS = {
    "web_search": web_search_stub,
    "reflection": reflection_tool,
    "python_sandbox": python_sandbox,
    "sql_query": sql_query_tool
}

def get_tool(tool_name: str):
    """Retrieves tool callable from the registry."""
    return TOOLS.get(tool_name)
