from typing import List, Dict, Any, Union, TypeVar
import copy
from app.schemas.state.models import AgentArtifact, ToolCall, PolicyViolation

T = TypeVar('T')

def append_messages(existing: List[Any], new: Union[List[Any], Any]) -> List[Any]:
    """Appends new messages safely without mutating the original list."""
    if existing is None:
        existing = []
    if not isinstance(new, list):
        new = [new]
    return existing + new

def deep_merge_artifacts(existing: Dict[str, AgentArtifact], new: Dict[str, AgentArtifact]) -> Dict[str, AgentArtifact]:
    """
    Safely merges new artifacts into the existing artifact dictionary using deepcopy.
    Avoids generic merges to prevent accidental overwrites of nested provenance structures.
    Reducers avoid in-place mutation to preserve deterministic checkpointing behavior and async execution safety.
    """
    merged = copy.deepcopy(existing) if existing else {}
    for key, val in (new or {}).items():
        merged[key] = copy.deepcopy(val)
    return merged

def append_tool_calls(existing: List[ToolCall], new: Union[List[ToolCall], ToolCall]) -> List[ToolCall]:
    """Appends tool calls immutably."""
    if existing is None:
        existing = []
    if not isinstance(new, list):
        new = [new]
    return existing + copy.deepcopy(new)

def append_routing_history(existing: List[str], new: Union[List[str], str]) -> List[str]:
    """Appends routing history elements immutably."""
    if existing is None:
        existing = []
    if not isinstance(new, list):
        new = [new]
    return existing + new

def append_violations(existing: List[PolicyViolation], new: Union[List[PolicyViolation], PolicyViolation]) -> List[PolicyViolation]:
    """Appends policy violations immutably."""
    if existing is None:
        existing = []
    if not isinstance(new, list):
        new = [new]
    return existing + copy.deepcopy(new)

def merge_token_usage(existing: Dict[str, int], new: Dict[str, int]) -> Dict[str, int]:
    """Merges token usage maps immutably."""
    merged = copy.copy(existing) if existing else {}
    for k, v in (new or {}).items():
        merged[k] = merged.get(k, 0) + v
    return merged
