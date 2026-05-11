from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import EvalRun, EvalCaseResult, EvalScore
from app.evals.cases.schema import EvalSeverity

REGRESSION_THRESHOLDS = {
    "answer_correctness": 0.05,
    "critique_alignment": 0.05,
    "latency": 0.10,
    "tool_efficiency": 0.05
}

def determine_severity(delta: float, threshold: float) -> EvalSeverity:
    if delta <= 0:
        return EvalSeverity.INFO # No regression
    if delta < threshold * 0.6:
        return EvalSeverity.INFO
    elif delta < threshold:
        return EvalSeverity.WARNING
    else:
        return EvalSeverity.CRITICAL

async def compare_eval_runs(session: AsyncSession, run_id_a: int, run_id_b: int) -> Dict[str, Any]:
    """Helper to compare average dimensional scores between two eval runs."""
    
    # In a real system, you would compute complex SQL aggregations here.
    # For now, it serves as a lightweight shim for regression comparisons.
    result = select(EvalScore).join(EvalCaseResult, EvalScore.result_id == EvalCaseResult.id).filter(EvalCaseResult.run_id.in_([run_id_a, run_id_b]))
    res = await session.execute(result)
    scores = res.scalars().all()
    
    return {
        "run_a": run_id_a,
        "run_b": run_id_b,
        "score_count": len(scores)
    }
