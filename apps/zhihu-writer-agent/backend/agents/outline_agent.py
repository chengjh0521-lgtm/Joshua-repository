from backend.config import read_prompt
from backend.services.deepseek_client import DeepSeekClient


class OutlineAgent:
    def __init__(self, client: DeepSeekClient, prompt_name: str = "outline.md") -> None:
        self.client = client
        self.prompt = read_prompt(prompt_name)

    async def create_outline(self, topic: str, evaluation_json: str, target_word_count: int | None = None) -> str:
        target_note = f"\n\n期望字数 target_word_count：{target_word_count}" if target_word_count else ""
        return await self.client.chat(
            self.prompt,
            f"选题：{topic}{target_note}\n\n选题评估 JSON：\n{evaluation_json}",
            temperature=0.6,
        )
