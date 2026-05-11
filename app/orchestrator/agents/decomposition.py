from app.schemas.state import AgentState
from app.orchestrator.tracing import with_agent_tracing
from langchain_core.runnables import RunnableConfig

@with_agent_tracing("decomposition")
async def decomposition_node(state: AgentState, config: RunnableConfig) -> dict:
    """Mock decomposition agent. Returns partial state without mutating original."""
    user_input = state.get("user_input", "")
    token_cost = len(user_input.split()) * 2  # Mock deterministic cost
    
    return {
        "routing_history": ["decomposition"],
        "token_usage_by_agent": {"decomposition": token_cost}
    }
