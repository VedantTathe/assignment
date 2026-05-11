from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import hashlib
from datetime import datetime, timezone

class PromptSpec(BaseModel):
    id: str = Field(..., description="Unique identifier for the prompt")
    version: str = Field(..., description="Semantic version string")
    role: str = Field(..., description="Role of the prompt (e.g. synthesis, critique)")
    template: str = Field(..., description="The actual prompt template text")
    expected_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for expected output")
    provider_constraints: List[str] = Field(default_factory=list, description="List of compatible providers")
    tags: List[str] = Field(default_factory=list, description="Metadata tags")
    parent_version: Optional[str] = Field(None, description="Lineage tracking for mutated prompts")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def checksum(self) -> str:
        """Deterministic checksum of the template for strict auditing."""
        return hashlib.sha256(self.template.encode('utf-8')).hexdigest()
