from backend.config import read_prompt
from backend.services.deepseek_client import DeepSeekClient


class WriterAgent:
    def __init__(self, client: DeepSeekClient, prompt_name: str = "write_article.md") -> None:
        self.client = client
        self.prompt = read_prompt(prompt_name)

    async def write(self, topic: str, outline: str) -> str:
        return await self.client.chat(
            self.prompt,
            f"选题：{topic}\n\n文章大纲：\n{outline}",
            temperature=0.75,
        )
