from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Any

import httpx

from config import PROJECT_ROOT, Settings


class DeepSeekClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.endpoint = f"{settings.deepseek_base_url}/chat/completions"

    def render_prompt(self, prompt_name: str, **values: Any) -> str:
        prompt_path = PROJECT_ROOT / "prompts" / prompt_name
        template = Template(prompt_path.read_text(encoding="utf-8"))
        safe_values = {key: str(value) for key, value in values.items()}
        return template.safe_substitute(**safe_values)

    def chat(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.settings.deepseek_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.settings.timeout_seconds) as client:
            response = client.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected DeepSeek response: {data}") from exc
