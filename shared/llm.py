import os
from typing import Optional, List
import httpx

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:4b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3-embedding:8b")


class QwenClient:
    """Client for Qwen 3.5 models via Ollama API."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or OLLAMA_BASE

    async def complete(self, prompt: str, system: str = "", model: Optional[str] = None, **kwargs) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model or LLM_MODEL,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                    **kwargs,
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, **kwargs) -> str:
        return await self.complete(
            prompt=user_prompt,
            system=system_prompt,
            temperature=temperature,
            **kwargs,
        )

    async def embed(self, text: str) -> List[float]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": EMBED_MODEL, "input": text},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"][0]


# Legacy wrapper kept for backward compatibility
async def generate(system_prompt: str, user_prompt: str, **kwargs) -> str:
    client = QwenClient()
    return await client.generate(system_prompt, user_prompt, **kwargs)
