import asyncio
import uuid
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.orchestrator.graph import graph
from app.evals.cases.schema import EvalCase
from app.evals.persistence.repository import create_eval_run, create_case_result, update_case_result, create_eval_score
from app.db.models import EvalRun
from app.evals.scoring.metrics import calculate_all_metrics
from app.core.logger import logger
from sqlalchemy.ext.asyncio import AsyncSession

async def evaluate_single_case(
    case: EvalCase, 
    run_id: int, 
    session_maker: Any, 
    semaphore: asyncio.Semaphore,
    provider_config: Dict[str, Any]
) -> Dict[str, Any]:
    async with semaphore:
        async with session_maker() as session:
            thread_id = f"eval-{case.id}-{uuid.uuid4().hex[:8]}"
            
            case_result = await create_case_result(
                session=session,
                run_id=run_id,
                case_id=case.id,
                thread_id=thread_id,
                input_query=case.input_query,
                prompt_version="1.0.0",
                adversarial=case.adversarial,
                tags=case.tags
            )
            
            initial_state = {
                "thread_id": thread_id,
                "user_input": case.input_query,
                "retry_count": 0
            }
            
            config = {
                "configurable": {
                    "db_session": session,
                    "token_limit": 8000,
                    **provider_config
                }
            }
            
            start_time = time.time()
            try:
                # Wrap real graph in a timeout boundary to preserve batch execution
                final_state = await asyncio.wait_for(graph.ainvoke(initial_state, config), timeout=60.0)
                
                final_response = final_state.get("final_response", "")
                
                await update_case_result(
                    session=session,
                    result_id=case_result.id,
                    final_response=final_response,
                    success_status="success"
                )
                
                metrics = calculate_all_metrics(final_state, case.expected_behavior)
                for m in metrics:
                    await create_eval_score(
                        session=session,
                        result_id=case_result.id,
                        dimension=m["dimension"],
                        score=m["score"],
                        justification=m["justification"],
                        metadata=m["metadata"]
                    )
                    
                logger.info(f"Eval case {case.id} completed successfully in {time.time() - start_time:.2f}s")
                return {"status": "success", "state": final_state}
                
            except asyncio.TimeoutError:
                await update_case_result(
                    session=session,
                    result_id=case_result.id,
                    final_response="",
                    success_status="failed",
                    error_details="Graph execution timed out"
                )
                logger.warning(f"Eval case {case.id} timed out.")
                return {"status": "timeout"}
                
            except Exception as e:
                await update_case_result(
                    session=session,
                    result_id=case_result.id,
                    final_response="",
                    success_status="failed",
                    error_details=str(e)
                )
                logger.exception(f"Eval case {case.id} crashed", error=str(e))
                return {"status": "error", "error": str(e)}

async def run_evaluation_suite(
    cases: List[EvalCase],
    dataset_name: str,
    session_maker: Any,
    concurrency_limit: int = 3,
    provider_config: Dict[str, Any] = None
) -> int:
    """Runs a batch of evaluation cases concurrently."""
    provider_config = provider_config or {}
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    async with session_maker() as session:
        eval_run = await create_eval_run(
            session=session,
            dataset_name=dataset_name,
            provider_metadata={"model": provider_config.get("model", "default")}
        )
        run_id = eval_run.id
    
    tasks = [
        evaluate_single_case(case, run_id, session_maker, semaphore, provider_config)
        for case in cases
    ]
    
    await asyncio.gather(*tasks)
    
    async with session_maker() as session:
        eval_run = await session.get(EvalRun, run_id)
        eval_run.completed_at = datetime.now(timezone.utc)
        await session.commit()
    
    return run_id
