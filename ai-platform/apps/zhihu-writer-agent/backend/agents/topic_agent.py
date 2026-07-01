from typing import Literal

from pydantic import BaseModel, Field

from backend.config import read_prompt
from backend.services.deepseek_client import DeepSeekClient


class TopicScores(BaseModel):
    finance_overlap: int = Field(ge=0, le=100)
    math_overlap: int = Field(ge=0, le=100)


class TopicEvaluation(BaseModel):
    passed: bool
    matched_direction: Literal["finance", "math", "both", "none"]
    scores: TopicScores
    reasons: list[str]
    suggestions: list[str] = []


class TopicAgent:
    def __init__(self, client: DeepSeekClient) -> None:
        self.client = client
        self.prompt = read_prompt("topic_score.md")

    async def evaluate(self, topic: str) -> TopicEvaluation:
        result = await self.client.json_chat(
            self.prompt,
            f"知乎文章选题：{topic}",
            temperature=0.2,
        )
        return TopicEvaluation.model_validate(result)
