import asyncio
import pytest
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.models import Base, EvalRun, EvalCaseResult, EvalScore
from app.evals.datasets.adversarial import ADVERSARIAL_CASES, STANDARD_CASES
from app.evals.runners.async_runner import run_evaluation_suite
from tests.test_llm_integration import MockLLMProvider
from sqlalchemy import select

engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, poolclass=StaticPool, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest.mark.asyncio
async def test_eval_harness_persistence_and_isolation():
    await init_db()
    
    # Run 2 cases concurrently using the MockLLMProvider
    test_cases = [STANDARD_CASES[0], ADVERSARIAL_CASES[1]]
    
    provider_config = {
        "llm_provider": MockLLMProvider()
    }
    
    run_id = await run_evaluation_suite(
        cases=test_cases,
        dataset_name="test_dataset_v1",
        session_maker=TestingSessionLocal,
        concurrency_limit=2,
        provider_config=provider_config
    )
    
    assert run_id > 0
    
    # Use a fresh session for verification queries
    async with TestingSessionLocal() as session:
        # Verify EvalRun
        run = await session.get(EvalRun, run_id)
        assert run is not None
        assert run.dataset_name == "test_dataset_v1"
        assert run.completed_at is not None
        
        # Verify Case Results
        res = await session.execute(select(EvalCaseResult).where(EvalCaseResult.run_id == run_id))
        results = res.scalars().all()
        assert len(results) == 2
        
        # Verify success and threading
        for r in results:
            assert r.success_status == "success"
            assert r.thread_id.startswith(f"eval-{r.case_id}-")
            
        # Verify dimensional scores
        res_scores = await session.execute(select(EvalScore).join(EvalCaseResult, EvalScore.result_id == EvalCaseResult.id).where(EvalCaseResult.run_id == run_id))
        scores = res_scores.scalars().all()
        assert len(scores) > 0
        
        # Ensure answer_correctness was recorded with a justification
        correctness_scores = [s for s in scores if s.dimension == "answer_correctness"]
        assert len(correctness_scores) == 2
        assert correctness_scores[0].justification is not None

async def run_all():
    print("\n--- Running Eval Harness Tests ---")
    await test_eval_harness_persistence_and_isolation()
    print("SUCCESS: test_eval_harness_persistence_and_isolation")
    print("\n==================================================")
    print("ALL EVAL HARNESS TESTS PASSED!")
    print("==================================================\n")

if __name__ == "__main__":
    asyncio.run(run_all())
