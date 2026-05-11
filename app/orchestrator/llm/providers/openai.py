import os
from typing import AsyncGenerator, Dict, List
from openai import AsyncOpenAI
from app.orchestrator.llm.providers.base import AsyncLLMProvider
from app.core.config import settings

class OpenAIProvider(AsyncLLMProvider):
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.OPENAI_API_KEY or "dummy",
            base_url=base_url or settings.OPENAI_BASE_URL
        )
        self.default_model = model or settings.MODEL_NAME
        
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        target_model = model or self.default_model
        response = await self.client.chat.completions.create(
            model=target_model,
            messages=messages,
            stream=True,
            **kwargs
        )
        
        async for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = getattr(chunk.choices[0].delta, "content", None)
                if delta:
                    yield delta
