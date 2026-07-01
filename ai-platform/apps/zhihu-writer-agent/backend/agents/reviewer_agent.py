from backend.config import read_prompt
from backend.services.deepseek_client import DeepSeekClient


class ReviewerAgent:
    def __init__(self, client: DeepSeekClient, prompt_name: str = "review_article.md") -> None:
        self.client = client
        self.prompt = read_prompt(prompt_name)

    async def review(self, topic: str, article: str) -> str:
        return await self.client.chat(
            self.prompt,
            f"选题：{topic}\n\n待审稿文章：\n{article}",
            temperature=0.25,
        )
