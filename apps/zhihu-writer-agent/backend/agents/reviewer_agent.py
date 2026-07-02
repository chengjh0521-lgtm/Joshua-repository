from backend.config import read_prompt
from backend.services.deepseek_client import DeepSeekClient


class ReviewerAgent:
    def __init__(self, client: DeepSeekClient, prompt_name: str = "review_article.md") -> None:
        self.client = client
        self.prompt = read_prompt(prompt_name)

    async def review(self, topic: str, article: str, target_word_count: int | None = None) -> str:
        target_note = f"\n\n期望字数 target_word_count：{target_word_count}" if target_word_count else ""
        return await self.client.chat(
            self.prompt,
            f"选题：{topic}{target_note}\n\n待审稿文章：\n{article}",
            temperature=0.25,
        )
