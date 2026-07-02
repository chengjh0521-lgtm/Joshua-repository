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
    target_word_count: int | None = None
    actual_word_count: int | None = None
    word_count_passed: bool | None = None
    paragraph_count: int | None = None
    average_paragraph_length: int | None = None
    longest_paragraph_length: int | None = None
    paragraph_natural: bool | None = None
    information_gain_score: int | None = None
    repetition_score: int | None = None
    ai_similarity_estimate: int | None = None


class FinalCheckAgent:
    def __init__(self, client: DeepSeekClient, prompt_name: str = "final_check.md") -> None:
        self.client = client
        self.prompt = read_prompt(prompt_name)

    async def check(self, topic: str, article: str, target_word_count: int | None = None) -> FinalCheck:
        target_note = f"\n\n期望字数 target_word_count：{target_word_count}" if target_word_count else ""
        result = await self.client.json_chat(
            self.prompt,
            f"选题：{topic}{target_note}\n\n终稿文章：\n{article}",
            temperature=0.2,
        )
        return FinalCheck.model_validate(result)
