import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.models import Base
from app.orchestrator.tracing.events import TraceEventType
from app.orchestrator.tracing.core import trace_event, reconstruct_timeline
from app.schemas.state.models import AgentArtifact

engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, poolclass=StaticPool, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def test_trace_event_and_reconstruct():
    print("\n--- Testing Trace Event & Timeline Reconstruction ---")
    await init_db()
    async with TestingSessionLocal() as session:
        thread_id = "test-thread-123"
        
        # 1. Trace AGENT_STARTED
        await trace_event(
            session=session,
            thread_id=thread_id,
            event_type=TraceEventType.AGENT_STARTED,
            agent_name="retrieval",
            metadata={"objective": "Search for docs"}
        )
        
        # 2. Trace TOOL_CALLED with nested Pydantic state snapshot
        mock_artifact = AgentArtifact(
            agent_name="retrieval",
            output_text="Test",
            citations=[],
            critique_issues=[],
            token_usage=10
        )
        
        await trace_event(
            session=session,
            thread_id=thread_id,
            event_type=TraceEventType.TOOL_CALLED,
            agent_name="retrieval",
            state_snapshot={"retrieval": mock_artifact},
            metadata={
                "tool_name": "web_search",
                "input_payload": {"q": "langgraph docs"}
            }
        )
        
        # 3. Reconstruct
        timeline = await reconstruct_timeline(session, thread_id)
        
        assert len(timeline) == 2, f"Expected 2 events, got {len(timeline)}"
        assert timeline[0]["event_type"] == "AGENT_STARTED"
        assert timeline[1]["event_type"] == "TOOL_CALLED"
        assert timeline[1]["metadata"]["tool_name"] == "web_search"
        assert timeline[1]["state_snapshot"]["retrieval"]["output_text"] == "Test"
        print("SUCCESS: Events correctly sequenced and retrieved.")
        print("SUCCESS: Pydantic State Snapshot securely serialized to JSON within Trace.")

async def test_policy_violation_trace():
    print("\n--- Testing Policy Violation Tracing ---")
    await init_db()
    async with TestingSessionLocal() as session:
        thread_id = "test-thread-456"
        
        await trace_event(
            session=session,
            thread_id=thread_id,
            event_type=TraceEventType.POLICY_VIOLATION,
            agent_name="critique",
            metadata={
                "violation_type": "hallucination",
                "description": "Generated non-existent API",
                "span": "import nonexistent"
            }
        )
        
        timeline = await reconstruct_timeline(session, thread_id)
        assert len(timeline) == 1
        assert timeline[0]["event_type"] == "POLICY_VIOLATION"
        print("SUCCESS: Policy Violation structured trace successfully persisted.")

async def run_all_tests():
    await init_db()
    await test_trace_event_and_reconstruct()
    await test_policy_violation_trace()
    print("\n" + "="*50)
    print("ALL TRACING TESTS PASSED SUCCESSFULLY!")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
