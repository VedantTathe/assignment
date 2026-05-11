from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List

class AsyncLLMProvider(ABC):
    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        pass
