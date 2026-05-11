from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid

from app.db.session import async_session
from app.db.models import (
    ExecutionTrace,
    EvalRun,
    EvalCaseResult,
    EvalScore,
    PromptRewriteProposal,
    PromptRegistry
)
from app.orchestrator.agents.meta_agent import meta_agent
from app.orchestrator.graph import graph
from app.schemas.state import AgentState

router = APIRouter()

@router.get("/traces")
async def get_traces():
    """Get execution traces from database."""
    return {"message": "Traces endpoint placeholder"}


@router.get("/evals/summary")
async def get_eval_summary(
    run_id: Optional[int] = Query(None, description="Latest eval run if not specified"),
    days: int = Query(7, description="Look back period in days")
):
    """
    Retrieve eval summary broken down by category (standard, ambiguous, adversarial).
    """
    async with async_session() as session:
        # Get latest eval run if not specified
        if not run_id:
            stmt = select(EvalRun).order_by(EvalRun.completed_at.desc()).limit(1)
            result = await session.execute(stmt)
            run = result.scalars().first()
            if not run:
                raise HTTPException(status_code=404, detail="No eval runs found")
            run_id = run.id
        
        # Get all case results for this run
        stmt = select(EvalCaseResult).where(EvalCaseResult.run_id == run_id)
        result = await session.execute(stmt)
        cases = result.scalars().all()
        
        # Aggregate by category
        summary = {
            "run_id": run_id,
            "total_cases": len(cases),
            "by_category": {
                "standard": {"passed": 0, "failed": 0, "avg_score": 0.0},
                "ambiguous": {"passed": 0, "failed": 0, "avg_score": 0.0},
                "adversarial": {"passed": 0, "failed": 0, "avg_score": 0.0}
            },
            "by_dimension": {}
        }
        
        scores_by_dimension = {}
        
        for case in cases:
            # Determine category
            category = "standard"
            if case.tags and case.tags.get("ambiguous"):
                category = "ambiguous"
            elif case.adversarial:
                category = "adversarial"
            
            # Count pass/fail
            if case.success_status == "success":
                summary["by_category"][category]["passed"] += 1
            else:
                summary["by_category"][category]["failed"] += 1
            
            # Get scores for this case
            stmt = select(EvalScore).where(EvalScore.result_id == case.id)
            score_result = await session.execute(stmt)
            scores = score_result.scalars().all()
            
            for score in scores:
                if score.dimension not in scores_by_dimension:
                    scores_by_dimension[score.dimension] = []
                scores_by_dimension[score.dimension].append(score.score)
        
        # Calculate averages
        for dimension, scores in scores_by_dimension.items():
            avg = sum(scores) / len(scores) if scores else 0.0
            summary["by_dimension"][dimension] = {
                "avg_score": round(avg, 3),
                "sample_count": len(scores)
            }
        
        # Calculate category averages
        for category in ["standard", "ambiguous", "adversarial"]:
            total = (summary["by_category"][category]["passed"] + 
                    summary["by_category"][category]["failed"])
            if total > 0:
                success_rate = (summary["by_category"][category]["passed"] / total) * 100
                summary["by_category"][category]["success_rate"] = round(success_rate, 1)
        
        return summary


@router.post("/prompts/approve")
async def approve_prompt_rewrite(
    proposal_id: int,
    approved: bool = True,
    approver: str = "system"
):
    """
    Approve or reject a proposed prompt rewrite.
    """
    async with async_session() as session:
        stmt = select(PromptRewriteProposal).where(
            PromptRewriteProposal.id == proposal_id
        )
        result = await session.execute(stmt)
        proposal = result.scalars().first()
        
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        if approved:
            # Update proposal status
            proposal.approval_status = "approved"
            proposal.approved_at = datetime.utcnow()
            proposal.approved_by = approver
            
            # Create or update prompt registry
            stmt = select(PromptRegistry).where(
                PromptRegistry.agent_name == proposal.agent_name,
                PromptRegistry.is_active == True
            )
            result = await session.execute(stmt)
            active_prompt = result.scalars().first()
            
            if active_prompt:
                # Mark old one as inactive
                active_prompt.is_active = False
            
            # Create new version
            max_version = 1
            if active_prompt:
                max_version = active_prompt.version + 1
            
            new_prompt = PromptRegistry(
                agent_name=proposal.agent_name,
                version=max_version,
                prompt_text=proposal.proposed_prompt,
                is_active=True,
                avg_eval_score=0.0
            )
            
            session.add(new_prompt)
        else:
            proposal.approval_status = "rejected"
        
        await session.commit()
        
        return {
            "proposal_id": proposal_id,
            "status": proposal.approval_status,
            "agent_name": proposal.agent_name,
            "approved_at": proposal.approved_at,
            "message": "Approval recorded" if approved else "Rejection recorded"
        }


@router.post("/evals/trigger-reeval")
async def trigger_reeval(
    case_ids: list = None,
    use_latest_prompt: bool = True
):
    """
    Re-run evaluation on previously failed cases using updated prompts.
    """
    if not case_ids:
        raise HTTPException(status_code=400, detail="No case_ids provided")
    
    async with async_session() as session:
        # Fetch the cases
        stmt = select(EvalCaseResult).where(
            EvalCaseResult.case_id.in_(case_ids)
        )
        result = await session.execute(stmt)
        cases = result.scalars().all()
        
        if not cases:
            raise HTTPException(status_code=404, detail="No cases found")
        
        reeval_results = []
        
        for case in cases:
            # Re-run the graph with the original input
            thread_id = str(uuid.uuid4())
            initial_state = {
                "thread_id": thread_id,
                "user_input": case.input_query,
                "retry_count": 0
            }
            
            try:
                config = {
                    "configurable": {
                        "db_session": session,
                        "stream_queue": None,
                        "token_limit": 4000
                    }
                }
                
                # Run graph
                await graph.ainvoke(initial_state, config)
                
                reeval_results.append({
                    "case_id": case.case_id,
                    "thread_id": thread_id,
                    "status": "completed"
                })
            except Exception as e:
                reeval_results.append({
                    "case_id": case.case_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        return {
            "reeval_count": len(reeval_results),
            "results": reeval_results,
            "message": f"Re-evaluated {len(reeval_results)} cases with latest prompts"
        }


@router.post("/meta-agent/analyze")
async def run_meta_agent_analysis(eval_run_id: int):
    """
    Trigger meta-agent to analyze eval failures and propose prompt rewrites.
    """
    async with async_session() as session:
        # Verify eval run exists
        stmt = select(EvalRun).where(EvalRun.id == eval_run_id)
        result = await session.execute(stmt)
        run = result.scalars().first()
        
        if not run:
            raise HTTPException(status_code=404, detail="Eval run not found")
        
        # Run meta-agent
        await meta_agent.run(session, eval_run_id)
        
        # Get proposals created
        stmt = select(PromptRewriteProposal).where(
            PromptRewriteProposal.approval_status == "pending"
        ).order_by(PromptRewriteProposal.created_at.desc()).limit(5)
        result = await session.execute(stmt)
        proposals = result.scalars().all()
        
        return {
            "eval_run_id": eval_run_id,
            "proposals_created": len(proposals),
            "proposals": [
                {
                    "id": p.id,
                    "agent_name": p.agent_name,
                    "estimated_improvement": p.estimated_improvement,
                    "failing_cases": len(p.failing_eval_cases),
                    "status": p.approval_status
                }
                for p in proposals
            ],
            "message": "Meta-agent analysis complete"
        }

