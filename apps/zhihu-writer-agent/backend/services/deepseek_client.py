import json
from typing import Any, Optional

import httpx

from backend.config import settings


class DeepSeekError(RuntimeError):
    pass


class DeepSeekClient:
    def __init__(self) -> None:
        if not settings.deepseek_api_key:
            raise DeepSeekError("DEEPSEEK_API_KEY is missing. Copy .env.example to .env and set it.")

        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.model = settings.deepseek_model

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
        response_format: Optional[dict[str, str]] = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise DeepSeekError(f"DeepSeek API error {response.status_code}: {response.text}")

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekError(f"Unexpected DeepSeek response: {data}") from exc

        return content.strip()

    async def json_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        content = await self.chat(
            system_prompt,
            user_prompt,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise DeepSeekError(f"DeepSeek did not return valid JSON: {content}") from exc
