"""
Meta-Agent: Analyzes evaluation failures and proposes prompt rewrites.
This agent runs after eval harness completion to identify underperforming prompts.
"""
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    EvalCaseResult,
    EvalScore,
    EvalRun,
    PromptRewriteProposal,
    PromptRegistry
)
from app.core.logger import logger


class MetaAgent:
    """
    Analyzes failed eval cases and generates prompt rewrite proposals.
    """
    
    def __init__(self):
        self.name = "meta_agent"
    
    async def analyze_eval_failures(
        self,
        session: AsyncSession,
        eval_run_id: int,
        threshold_score: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Analyze eval failures and return structured failure analysis.
        """
        # Get all failed cases from this eval run
        stmt = select(EvalCaseResult).where(
            EvalCaseResult.run_id == eval_run_id,
            EvalCaseResult.success_status == "failed"
        )
        failed_cases = await session.execute(stmt)
        failed_cases = failed_cases.scalars().all()
        
        if not failed_cases:
            logger.info(f"No failed cases in eval run {eval_run_id}")
            return []
        
        # Group failures by agent
        failures_by_agent = {}
        for case in failed_cases:
            agent = case.tags.get("agent_name", "unknown") if case.tags else "unknown"
            if agent not in failures_by_agent:
                failures_by_agent[agent] = []
            failures_by_agent[agent].append({
                "case_id": case.case_id,
                "input": case.input_query,
                "error": case.error_details,
                "failure_types": case.failure_types
            })
        
        # Calculate agent performance
        agent_performance = {}
        for agent_name in failures_by_agent.keys():
            stmt = select(func.count(EvalCaseResult.id)).where(
                EvalCaseResult.run_id == eval_run_id,
                EvalCaseResult.tags.contains({agent_name: True})
            )
            total = await session.execute(stmt)
            total_cases = total.scalar() or 1
            
            failed_count = len(failures_by_agent[agent_name])
            success_rate = (total_cases - failed_count) / total_cases
            
            agent_performance[agent_name] = {
                "success_rate": success_rate,
                "failed_cases": failed_count,
                "total_cases": total_cases,
                "failures": failures_by_agent[agent_name]
            }
        
        return agent_performance
    
    async def generate_prompt_rewrite_proposal(
        self,
        session: AsyncSession,
        agent_name: str,
        current_performance: Dict[str, Any],
        current_prompt: str
    ) -> Optional[PromptRewriteProposal]:
        """
        Generate a prompt rewrite proposal for a poorly performing agent.
        """
        failed_cases = current_performance.get("failures", [])
        
        if not failed_cases:
            return None
        
        # Analyze failure patterns
        failure_patterns = self._extract_failure_patterns(failed_cases)
        
        # Generate improved prompt
        improved_prompt = self._generate_improved_prompt(
            agent_name,
            current_prompt,
            failure_patterns
        )
        
        # Create diff summary
        diff_summary = self._generate_diff_summary(current_prompt, improved_prompt)
        
        # Generate justification
        justification = f"""
        Analysis of {len(failed_cases)} failed test cases revealed:
        - Common failure patterns: {', '.join(failure_patterns.get('patterns', [])[:3])}
        - Root cause: {failure_patterns.get('root_cause', 'Unknown')}
        
        Proposed improvements:
        - Enhanced clarity in instructions
        - Better handling of edge cases
        - Improved structure and formatting
        """
        
        # Create proposal
        proposal = PromptRewriteProposal(
            agent_name=agent_name,
            current_prompt=current_prompt,
            proposed_prompt=improved_prompt,
            diff_summary=diff_summary,
            justification=justification.strip(),
            failing_eval_cases=[c["case_id"] for c in failed_cases],
            estimated_improvement=0.15,  # Estimated 15% improvement
            approval_status="pending"
        )
        
        await session.add(proposal)
        await session.commit()
        
        logger.info(f"Created prompt rewrite proposal for {agent_name}")
        return proposal
    
    def _extract_failure_patterns(self, failed_cases: List[Dict]) -> Dict[str, Any]:
        """Extract common patterns from failures."""
        patterns = []
        
        for case in failed_cases:
            failure_types = case.get("failure_types", [])
            patterns.extend(failure_types)
        
        # Count pattern frequency
        pattern_counts = {}
        for pattern in patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        most_common = sorted(
            pattern_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "patterns": [p[0] for p in most_common[:5]],
            "root_cause": most_common[0][0] if most_common else "Unknown",
            "frequency": pattern_counts
        }
    
    def _generate_improved_prompt(
        self,
        agent_name: str,
        current_prompt: str,
        failure_patterns: Dict[str, Any]
    ) -> str:
        """Generate an improved prompt based on failure analysis."""
        
        improvements = {
            "synthesis": self._improve_synthesis_prompt,
            "critique": self._improve_critique_prompt,
            "retrieval": self._improve_retrieval_prompt,
            "decomposition": self._improve_decomposition_prompt
        }
        
        improvement_func = improvements.get(agent_name, lambda *args: current_prompt)
        return improvement_func(current_prompt, failure_patterns)
    
    def _improve_synthesis_prompt(self, current: str, patterns: Dict) -> str:
        """Generate improved synthesis prompt."""
        improvements = f"""
        {current}
        
        === IMPROVEMENTS FOR FAILING CASES ===
        
        Key guidelines to address identified issues:
        1. Ensure ALL citations are properly formatted
        2. Cross-reference multiple sources before synthesizing
        3. For contradictory information, explicitly note the conflict
        4. Validate facts against retrieved context before including them
        5. Add uncertainty markers when confidence is low
        
        Common failure patterns addressed:
        - Hallucinations: Only use information explicitly in retrieved context
        - Grounding errors: Always cite the source for each claim
        - Tone inconsistency: Maintain professional, neutral tone throughout
        """
        return improvements.strip()
    
    def _improve_critique_prompt(self, current: str, patterns: Dict) -> str:
        """Generate improved critique prompt."""
        improvements = f"""
        {current}
        
        === IMPROVEMENTS FOR FAILING CASES ===
        
        Enhanced critique guidelines:
        1. Use specific, measurable criteria for evaluation
        2. Provide concrete examples of issues found
        3. Suggest specific fixes, not just problems
        4. Cross-reference against the original query requirements
        5. Check for internal contradictions in reasoning
        
        Failure patterns to watch for:
        - Missed hallucinations
        - Ungrounded claims
        - Missing citations
        """
        return improvements.strip()
    
    def _improve_retrieval_prompt(self, current: str, patterns: Dict) -> str:
        """Generate improved retrieval prompt."""
        improvements = f"""
        {current}
        
        === IMPROVEMENTS FOR FAILING CASES ===
        
        Enhanced retrieval guidelines:
        1. Diversify search queries for better coverage
        2. Handle edge cases and ambiguous queries explicitly
        3. Prioritize authoritative sources
        4. Extract both direct answers and supporting context
        5. Handle "no results found" cases gracefully
        """
        return improvements.strip()
    
    def _improve_decomposition_prompt(self, current: str, patterns: Dict) -> str:
        """Generate improved decomposition prompt."""
        improvements = f"""
        {current}
        
        === IMPROVEMENTS FOR FAILING CASES ===
        
        Enhanced decomposition guidelines:
        1. Break complex queries into atomic sub-questions
        2. Identify dependencies between sub-questions
        3. Handle ambiguous queries by asking clarifying questions
        4. Consider multi-modal aspects if applicable
        5. Validate that sub-questions are exhaustive
        """
        return improvements.strip()
    
    def _generate_diff_summary(self, old: str, new: str) -> str:
        """Generate a summary of changes between prompts."""
        old_lines = old.split("\n")
        new_lines = new.split("\n")
        
        # Simple diff: count new lines added
        new_count = len(new_lines) - len(old_lines)
        
        summary = f"Added {new_count} new lines with improved guidelines and failure pattern handling."
        return summary
    
    async def run(self, session: AsyncSession, eval_run_id: int):
        """Main entry point for meta-agent."""
        logger.info(f"Meta-agent analyzing eval run {eval_run_id}")
        
        # Analyze failures
        performance_analysis = await self.analyze_eval_failures(
            session,
            eval_run_id,
            threshold_score=0.6
        )
        
        # Generate proposals for underperforming agents
        for agent_name, performance in performance_analysis.items():
            if performance["success_rate"] < 0.8:  # 80% success threshold
                
                # Get current prompt
                stmt = select(PromptRegistry).where(
                    PromptRegistry.agent_name == agent_name,
                    PromptRegistry.is_active == True
                )
                result = await session.execute(stmt)
                prompt_record = result.scalars().first()
                
                if prompt_record:
                    await self.generate_prompt_rewrite_proposal(
                        session,
                        agent_name,
                        performance,
                        prompt_record.prompt_text
                    )


# Singleton instance
meta_agent = MetaAgent()
