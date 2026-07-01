from backend.config import read_prompt
from backend.services.deepseek_client import DeepSeekClient


class RewriteAgent:
    def __init__(self, client: DeepSeekClient, prompt_name: str = "rewrite_article.md") -> None:
        self.client = client
        self.prompt = read_prompt(prompt_name)

    async def rewrite(self, topic: str, draft: str, review: str) -> str:
        return await self.client.chat(
            self.prompt,
            f"选题：{topic}\n\n初稿：\n{draft}\n\n审稿意见：\n{review}",
            temperature=0.7,
        )
