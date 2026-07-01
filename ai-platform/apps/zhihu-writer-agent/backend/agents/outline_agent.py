from backend.config import read_prompt
from backend.services.deepseek_client import DeepSeekClient


class OutlineAgent:
    def __init__(self, client: DeepSeekClient, prompt_name: str = "outline.md") -> None:
        self.client = client
        self.prompt = read_prompt(prompt_name)

    async def create_outline(self, topic: str, evaluation_json: str) -> str:
        return await self.client.chat(
            self.prompt,
            f"选题：{topic}\n\n选题评估 JSON：\n{evaluation_json}",
            temperature=0.6,
        )
