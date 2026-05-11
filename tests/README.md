# Shared State Management Testing Suite

This directory contains the validation and testing suite for the LangGraph-compatible shared state management system. 

## Purpose
The state testing suite validates that our core schema, reducers, and helper utilities function deterministically before any orchestration logic is laid down. This ensures:
1. **Serialization Safety**: Pydantic models (with `datetime` and nested structures) can be correctly marshaled to pure JSON format using `safe_json_serialize()` for persistent LangGraph checkpoints.
2. **Mutation Safety**: The graph's reducers (such as `deep_merge_artifacts`) successfully utilize `deepcopy` mechanisms to avoid mutable leaks between node executions (e.g. retrying critique nodes overwriting old artifacts).
3. **Data Integrity**: Pydantic field validators block strictly invalid input (like confidence scores outside 0.0 to 1.0).

## How to Run

Execute the validation script natively through the Python interpreter. Ensure your virtual environment is active so it resolves local imports properly.

```bash
python -m tests.test_state
```

## Expected Successful Outputs
You should observe 4 distinct testing stages complete successfully:

1. **Pydantic Validation**: An intentional failure should be triggered and gracefully handled, confirming the schema rejects invalid data.
2. **JSON Serialization**: Dates, lists, and base models should convert successfully and prove `json.dumps()` compatibility.
3. **Deepcopy Mutation Isolation**: A simulated state update will occur, followed by a mutation of the original object, proving the merged graph state remains entirely unaffected.
4. **AgentState Composition**: A fully nested `AgentState` object will be formulated and safely logged to the console confirming the TypedDict functions perfectly with `safe_json_serialize()`.

The suite will conclude with:
`ALL TESTS PASSED SUCCESSFULLY! The shared state system is production-ready.`
