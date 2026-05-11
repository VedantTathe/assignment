from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import EvalRun, EvalCaseResult, EvalScore

async def create_eval_run(session: AsyncSession, dataset_name: str, provider_metadata: Dict[str, Any] = None) -> EvalRun:
    new_run = EvalRun(
        dataset_name=dataset_name,
        provider_metadata=provider_metadata
    )
    session.add(new_run)
    await session.commit()
    await session.refresh(new_run)
    return new_run

async def create_case_result(session: AsyncSession, run_id: int, case_id: str, thread_id: str, input_query: str, prompt_version: str, adversarial: bool, tags: list) -> EvalCaseResult:
    result = EvalCaseResult(
        run_id=run_id,
        case_id=case_id,
        thread_id=thread_id,
        input_query=input_query,
        prompt_version=prompt_version,
        adversarial=adversarial,
        tags=tags,
        success_status="pending"
    )
    session.add(result)
    await session.commit()
    await session.refresh(result)
    return result

async def update_case_result(session: AsyncSession, result_id: int, final_response: str, success_status: str, error_details: str = None, execution_trace_id: int = None):
    result = await session.get(EvalCaseResult, result_id)
    if result:
        result.final_response = final_response
        result.success_status = success_status
        result.error_details = error_details
        if execution_trace_id:
            result.execution_trace_id = execution_trace_id
        await session.commit()

async def create_eval_score(session: AsyncSession, result_id: int, dimension: str, score: float, justification: str, metadata: Dict[str, Any] = None):
    new_score = EvalScore(
        result_id=result_id,
        dimension=dimension,
        score=score,
        justification=justification,
        metadata_json=metadata
    )
    session.add(new_score)
    await session.commit()
