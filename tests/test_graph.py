import asyncio
import os
from typing import Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.models import Base
from app.schemas.state import AgentState
from app.orchestrator.graph import graph
from app.orchestrator.tracing.core import reconstruct_timeline
from tests.test_llm_integration import MockLLMProvider

engine = create_async_engine("sqlite+aiosqlite:///test_graph.db", echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def init_db():
    if os.path.exists("test_graph.db"):
        os.remove("test_graph.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def run_successful_flow():
    print("\n--- Testing Successful Orchestration Flow ---")
    async with TestingSessionLocal() as session:
        initial_state = {
            "thread_id": "success-thread-1",
            "user_input": "Tell me about LangGraph",
            "retry_count": 0
        }
        
        config = {
            "configurable": {
                "db_session": session, 
                "token_limit": 4000,
                "llm_provider": MockLLMProvider()
            }
        }
        final_state = await graph.ainvoke(initial_state, config)
        
        assert "decomposition" in final_state["routing_history"]
        assert "retrieval" in final_state["routing_history"]
        assert "synthesis" in final_state["routing_history"]
        assert "critique_passed" in final_state["routing_history"]
        assert "compression" not in final_state["routing_history"]
        
        # Verify artifact versioning
        assert "synthesis_v0" in final_state["agent_artifacts"]
        
        print("SUCCESS: Standard flow executed correctly.")
        
        # Verify traces
        timeline = await reconstruct_timeline(session, "success-thread-1")
        assert len(timeline) > 0
        print(f"SUCCESS: Traced {len(timeline)} events.")

async def run_retry_flow():
    print("\n--- Testing Critique Retry Flow with Versioning ---")
    async with TestingSessionLocal() as session:
        initial_state = {
            "thread_id": "retry-thread-2",
            "user_input": "This is an ambiguous query",
            "retry_count": 0
        }
        
        config = {
            "configurable": {
                "db_session": session, 
                "token_limit": 4000,
                "llm_provider": MockLLMProvider()
            }
        }
        final_state = await graph.ainvoke(initial_state, config)
        
        assert "critique_failed" in final_state["routing_history"]
        assert "critique_passed" in final_state["routing_history"]
        assert final_state["retry_count"] == 1
        
        # Verify artifact versioning isolation
        assert "synthesis_v0" in final_state["agent_artifacts"]
        assert "synthesis_v1" in final_state["agent_artifacts"]
        print("SUCCESS: Artifacts correctly versioned (v0 and v1 preserved).")

async def run_compression_flow():
    print("\n--- Testing Budget Manager / Compression Routing ---")
    async with TestingSessionLocal() as session:
        initial_state = {
            "thread_id": "budget-thread-3",
            "user_input": "Query",
            "retry_count": 0,
            "token_usage_by_agent": {"mock_prior": 5000} # Exceeds budget
        }
        
        config = {
            "configurable": {
                "db_session": session, 
                "token_limit": 4000,
                "llm_provider": MockLLMProvider()
            }
        }
        final_state = await graph.ainvoke(initial_state, config)
        
        assert "compression" in final_state["routing_history"]
        print("SUCCESS: Budget check correctly routed to compression.")

async def run_all():
    await init_db()
    await run_successful_flow()
    await run_retry_flow()
    await run_compression_flow()
    print("\n" + "="*50)
    print("ALL GRAPH ORCHESTRATION TESTS PASSED!")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(run_all())
