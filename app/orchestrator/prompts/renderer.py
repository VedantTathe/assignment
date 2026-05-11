from typing import Dict, Any, List
from app.orchestrator.prompts.schema import PromptSpec

class PromptRenderer:
    @staticmethod
    def render(spec: PromptSpec, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Safely renders a prompt spec into a structured provider-agnostic message array.
        Enforces separation of concerns so orchestration nodes don't string-format directly.
        """
        # Ensure all expected keys exist to prevent KeyError
        safe_context = {k: context.get(k, "") for k in ["user_input", "retrieved_context", "critique_feedback"]}
        
        rendered_content = spec.template.format(**safe_context)
            
        return [
            {"role": "system", "content": "You are a specialized agent following strict instructions."},
            {"role": "user", "content": rendered_content}
        ]
