import json
import copy
from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import ValidationError

from app.schemas.state.models import (
    ToolCall, Citation, CritiqueIssue, AgentArtifact, PolicyViolation
)
from app.schemas.state.core import AgentState
from app.schemas.state.helpers import safe_json_serialize
from app.schemas.state.reducers import deep_merge_artifacts

def print_section(title: str):
    print(f"\n{'='*50}\n--- {title} ---\n{'='*50}")

def test_pydantic_validation():
    print_section("1. Testing Pydantic Validation & Schema Rejection")
    
    try:
        # Intentional error: confidence should be between 0.0 and 1.0
        CritiqueIssue(
            span="test",
            issue_type="hallucination",
            confidence=1.5, # Exceeds 1.0 upper limit
            explanation="Bad confidence",
            suggested_fix="fix"
        )
        print("FAIL: Validation did not catch out-of-bounds confidence!")
        assert False
    except ValidationError as e:
        print("SUCCESS: Caught invalid schema for CritiqueIssue (confidence out of bounds).")
        print(f"Error details: {e.errors()[0]['msg']}")

def test_model_dump_and_serialization():
    print_section("2. Testing JSON Serialization & Model Dumping")
    
    citation = Citation(
        chunk_id="chunk-123",
        source_url="https://example.com/doc",
        supporting_text="This is a test document.",
        referenced_sentences=["It is a test."]
    )
    
    violation = PolicyViolation(
        violation_type="format_error",
        description="Incorrect format provided",
        timestamp=datetime.now(timezone.utc)
    )
    
    # Test model_dump
    dumped_citation = citation.model_dump()
    assert isinstance(dumped_citation, dict)
    print("SUCCESS: model_dump() produced a valid dictionary.")
    
    # Test model_dump_json
    json_citation = citation.model_dump_json()
    assert isinstance(json_citation, str)
    print("SUCCESS: model_dump_json() produced a valid JSON string.")
    
    # Test safe_json_serialize with datetime
    serialized_violation = safe_json_serialize(violation)
    assert isinstance(serialized_violation["timestamp"], str)
    print("SUCCESS: safe_json_serialize handled datetime conversion perfectly.")
    
    # Ensure json.dumps works on serialized object
    try:
        json.dumps(serialized_violation)
        print("SUCCESS: Serialized violation is safely convertible via json.dumps().")
    except TypeError as e:
        print(f"FAIL: JSON serialization failed: {e}")
        assert False

def test_deepcopy_mutation_isolation():
    print_section("3. Testing Deepcopy and Mutation Isolation")
    
    # Create an initial artifact
    artifact_a = AgentArtifact(
        agent_name="synthesis",
        output_text="Initial synthesis.",
        citations=[],
        critique_issues=[],
        token_usage=100
    )
    
    state_dict_1: Dict[str, AgentArtifact] = {"synthesis": artifact_a}
    
    # A retrying node provides an updated artifact
    updated_artifact = AgentArtifact(
        agent_name="synthesis",
        output_text="Updated synthesis.",
        citations=[],
        critique_issues=[],
        token_usage=150
    )
    
    state_dict_2: Dict[str, AgentArtifact] = {"synthesis": updated_artifact}
    
    # Merge using reducer
    merged_state = deep_merge_artifacts(state_dict_1, state_dict_2)
    
    # Mutate the original updated_artifact to check isolation
    updated_artifact.output_text = "Mutated text!"
    
    assert merged_state["synthesis"].output_text == "Updated synthesis.", "Mutation leaked into merged state!"
    print("SUCCESS: Reducer isolated the nested mutation using deepcopy.")
    print(f"Original mutated to: '{updated_artifact.output_text}'")
    print(f"Merged state preserved: '{merged_state['synthesis'].output_text}'")

def test_full_agent_state():
    print_section("4. Testing Full AgentState TypedDict Composition")
    
    tool_call = ToolCall(
        tool_name="web_search",
        input_payload={"query": "LangGraph best practices"},
        output_payload={"result": "Docs link"},
        latency_ms=120,
        accepted_by_agent=True,
        retry_attempt=0,
        status="success"
    )
    
    artifact = AgentArtifact(
        agent_name="retrieval",
        output_text="Retrieved documents",
        citations=[Citation(
            chunk_id="ch-01",
            source_url="http://docs",
            supporting_text="Docs",
            referenced_sentences=["Docs"]
        )],
        critique_issues=[],
        token_usage=50
    )
    
    # Constructing a simulated AgentState
    state: AgentState = {
        "thread_id": "thread-456",
        "user_input": "How to manage state?",
        "messages": [{"role": "user", "content": "How to manage state?"}],
        "agent_artifacts": {"retrieval": artifact},
        "tool_calls": [tool_call],
        "routing_history": ["retrieval"],
        "policy_violations": [],
        "token_usage_by_agent": {"retrieval": 50},
        "retry_count": 0,
        "final_response": None
    }
    
    print("SUCCESS: Constructed realistic AgentState.")
    print("Printing safe JSON serialization of full state:")
    
    safe_state = safe_json_serialize(state)
    pretty_json = json.dumps(safe_state, indent=2)
    print(pretty_json)

if __name__ == "__main__":
    print("\nStarting Shared State Management Validation Suite...\n")
    test_pydantic_validation()
    test_model_dump_and_serialization()
    test_deepcopy_mutation_isolation()
    test_full_agent_state()
    print("\n" + "="*50)
    print("ALL TESTS PASSED SUCCESSFULLY! The shared state system is production-ready.")
    print("="*50 + "\n")
