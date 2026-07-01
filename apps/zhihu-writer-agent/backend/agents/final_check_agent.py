from typing import Literal

from pydantic import BaseModel

from backend.config import read_prompt
from backend.services.deepseek_client import DeepSeekClient


class FinalCheck(BaseModel):
    recommend_publish: bool
    suggested_title: str
    risk_level: Literal["low", "medium", "high"]
    final_notes: list[str]
    manual_operation_suggestions: list[str] = []


class FinalCheckAgent:
    def __init__(self, client: DeepSeekClient, prompt_name: str = "final_check.md") -> None:
        self.client = client
        self.prompt = read_prompt(prompt_name)

    async def check(self, topic: str, article: str) -> FinalCheck:
        result = await self.client.json_chat(
            self.prompt,
            f"选题：{topic}\n\n终稿文章：\n{article}",
            temperature=0.2,
        )
        return FinalCheck.model_validate(result)
