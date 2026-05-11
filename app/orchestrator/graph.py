from langgraph.graph import StateGraph, END
from app.schemas.state import AgentState
from app.orchestrator.agents.decomposition import decomposition_node
from app.orchestrator.agents.retrieval import retrieval_node
from app.orchestrator.agents.synthesis import synthesis_node
from app.orchestrator.agents.critique import critique_node, critique_router
from app.orchestrator.agents.compression import compression_node
from app.orchestrator.budget import check_budget

def create_async_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("decomposition", decomposition_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("compression", compression_node)
    
    workflow.set_entry_point("decomposition")
    workflow.add_edge("decomposition", "retrieval")
    
    workflow.add_conditional_edges(
        "retrieval",
        check_budget,
        {
            "synthesis": "synthesis",
            "compression": "compression"
        }
    )
    
    workflow.add_edge("compression", "synthesis")
    workflow.add_edge("synthesis", "critique")
    
    workflow.add_conditional_edges(
        "critique",
        critique_router,
        {
            "synthesis": "synthesis",
            "END": END
        }
    )
    
    return workflow.compile()

graph = create_async_graph()
