from app.schemas.state import AgentState
from typing import Dict, Any, List

def evaluate_answer_correctness(state: AgentState, expected_behavior: str) -> Dict[str, Any]:
    # Deterministic heuristic scoring initially, as requested
    final_response = state.get("final_response", "")
    if not final_response:
        return {"score": 0.0, "justification": "No final response generated", "metadata": {}}
    
    if "failed" in final_response.lower() or "error" in final_response.lower():
        return {"score": 0.5, "justification": "Response generated but contains error indicators", "metadata": {}}
        
    return {"score": 1.0, "justification": "Response generated successfully", "metadata": {"length": len(final_response)}}

def evaluate_critique_alignment(state: AgentState) -> Dict[str, Any]:
    history = state.get("routing_history", [])
    retry_count = state.get("retry_count", 0)
    
    if "critique_failed" in history and retry_count > 0:
        return {"score": 1.0, "justification": "Critique triggered retry successfully", "metadata": {"retries": retry_count}}
    
    if "critique_passed" in history and retry_count == 0:
        return {"score": 1.0, "justification": "Passed critique on first try", "metadata": {}}
        
    return {"score": 0.0, "justification": "Critique behavior ambiguous or failed to execute properly", "metadata": {"history": history}}

def calculate_all_metrics(state: AgentState, expected_behavior: str) -> List[Dict[str, Any]]:
    return [
        {"dimension": "answer_correctness", **evaluate_answer_correctness(state, expected_behavior)},
        {"dimension": "critique_alignment", **evaluate_critique_alignment(state)}
    ]
